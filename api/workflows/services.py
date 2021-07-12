from typing import List
import asyncio
import json
import pytz
import time
import datetime as dt
from django.db import transaction
import polling

from app.celery import app

from workflows.models import (
    Workflow,
    WorkflowRun,
    WorkflowNotebookMap,
    STATUS_SUCCESS,
    STATUS_ERROR,
    STATUS_ALWAYS,
    STATUS_RUNNING,
    STATUS_QUEUED,
    STATUS_ABORTED
)
from workflows.serializers import WorkflowSerializer, WorkflowRunSerializer
from utils.apiResponse import ApiResponse
from utils.zeppelinAPI import Zeppelin

from genie.tasks import runNotebookJob as runNotebookJobTask
from genie.services import NotebookJobServices
from genie.models import CustomSchedule, RunStatus, NOTEBOOK_STATUS_RUNNING, NOTEBOOK_STATUS_SUCCESS, NOTEBOOK_STATUS_QUEUED, NOTEBOOK_STATUS_ABORT

from django_celery_beat.models import CrontabSchedule, PeriodicTask
# Name of the celery task which calls the zeppelin api
CELERY_TASK_NAME = "genie.tasks.runNotebookJob"


class WorkflowServices:
    """
    Class containing services related to NotebookJob model
    """

    @staticmethod
    def getWorkflows(offset: int = 0, limit: int = 25, sortColumn : str = None, sortOrder : str = None):
        """
        Service to fetch and serialize Workflows
        :param offset: Offset for fetching NotebookJob objects
        """
        res = ApiResponse(message="Error retrieving workflows")
        workflows = Workflow.objects.order_by("-id")
        total = workflows.count()

        if(sortColumn):
            workflows = WorkflowServices.sortingOnWorkflows(workflows, sortColumn, sortOrder)
        data = WorkflowSerializer(workflows[offset : offset+limit], many=True).data

        res.update(
            True,
            "Workflows retrieved successfully",
            {"total": total, "workflows": data},
        )
        return res

    @staticmethod
    def sortingOnWorkflows(workflows, sortColumn, sortOrder):
        if sortColumn == 'name' and sortOrder == "ascend":
            workflows = Workflow.objects.filter(enabled=True).order_by("name")

        if sortColumn == 'name' and sortOrder == "descend":
            workflows = Workflow.objects.filter(enabled=True).order_by("-name")

        if sortColumn == 'triggerWorkflow' and sortOrder == "ascend":
            workflows = Workflow.objects.filter(enabled=True).order_by("triggerWorkflow__name")

        if sortColumn == 'triggerWorkflow' and sortOrder == "descend":
            workflows = Workflow.objects.filter(enabled=True).order_by("-triggerWorkflow__name")

        if sortColumn == "schedule" and sortOrder == "ascend":
            workflows = Workflow.objects.filter(enabled=True).order_by("crontab__customschedule__name")

        if sortColumn == "schedule" and sortOrder == "descend":
            workflows = Workflow.objects.filter(enabled=True).order_by("-crontab__customschedule__name")

        if sortColumn == "lastRunTime" and sortOrder == "ascend":
            workflows = Workflow.objects.filter(enabled=True).order_by("last_run_at")
        if sortColumn == "lastRunTime" and sortOrder == "descend":
            workflows = Workflow.objects.filter(enabled=True).order_by("-last_run_at")

        # if sortColumn == "lastRunStatus" and sortOrder == "ascend":
        #     workflows = Workflow.objects.filter(enabled=True).order_by("workflowrun__status")

        # if sortColumn == "lastRunStatus" and sortOrder == "descend":
        #     workflows = Workflow.objects.filter(enabled=True).order_by("workflowrun__status")

        return workflows



    @staticmethod
    @transaction.atomic
    def createWorkflow(
        name: str,
        scheduleId: int,
        triggerWorkflowId: int,
        triggerWorkflowStatus: str,
        notebookIds: List[int],
    ):
        """
        Creates workflow
        :param name: name of new workflow
        :param scheduleId: crontab id
        :param triggerWorkflowId: id of workflow which triggers this workflow
        :param triggerWorkflowStatus: ["success", "failure", "always"] required
                status of triggerWorkflow to trigger this workflow
        :param notebookIds: notebookIds for workflow
        """
        res = ApiResponse(message="Error in creating workflow")
        periodictask = None
        workflow = Workflow.objects.create(
            name=name,
            periodictask=periodictask,
            triggerWorkflow_id=triggerWorkflowId,
            triggerWorkflowStatus=triggerWorkflowStatus
        )
        if scheduleId:
            periodictask = PeriodicTask.objects.create(
                crontab_id=scheduleId,
                name=name,
                task="workflows.tasks.runWorkflowJob",
                args = str([workflow.id])
            )
            workflow.periodictask = periodictask
            workflow.save()
        
        notebookJobs = [
            WorkflowNotebookMap(workflow_id=workflow.id, notebookId=notebookId)
            for notebookId in notebookIds
        ]
        WorkflowNotebookMap.objects.bulk_create(notebookJobs)
        res.update(True, "Workflow created successfully", workflow.id)
        return res

    @staticmethod
    @transaction.atomic
    def updateWorkflow(
        id: int,
        name: str,
        scheduleId: int,
        triggerWorkflowId: int,
        triggerWorkflowStatus: str,
        notebookIds: List[int],
    ):
        """
        Updates workflow
        :param name: name of new workflow
        :param scheduleId: crontab id
        :param triggerWorkflowId: id of workflow which triggers this workflow
        :param triggerWorkflowStatus: ["success", "failure", "always"] required
                status of triggerWorkflow to trigger this workflow
        :param notebookIds: notebookIds for workflow
        """
        res = ApiResponse(message="Error in updating workflow")
        workflow = Workflow.objects.get(id=id)
        if not workflow:
            return res

        workflow.name = name
        workflow.triggerWorkflow_id = triggerWorkflowId
        workflow.triggerWorkflowStatus = triggerWorkflowStatus
        workflow.save()
        if scheduleId:
            if workflow.periodictask:
                workflow.periodictask.crontab_id = scheduleId
                workflow.periodictask.save()
            else:
                periodictask = PeriodicTask.objects.create(
                    crontab_id=scheduleId,
                    name=name,
                    task="workflows.tasks.runWorkflowJob",
                    args = str([workflow.id])
                )
                workflow.periodictask = periodictask
                workflow.save()
        else:
            if workflow.periodictask:
                PeriodicTask.objects.get(id=workflow.periodictask).delete()
                workflow.periodictask = None
                workflow.save()
            
        WorkflowNotebookMap.objects.filter(workflow_id=id).delete()
        notebookJobs = [
            WorkflowNotebookMap(workflow_id=id, notebookId=notebookId)
            for notebookId in notebookIds
        ]
        WorkflowNotebookMap.objects.bulk_create(notebookJobs)
        res.update(True, "Workflow updated successfully", None)
        return res

    @staticmethod
    def deleteWorkflow(workflowId: int):
        """
        Delete workflow
        :param workflowId: id of Workflows.Workflow
        """
        res = ApiResponse(message="Error in deleting workflow logs")
        Workflow.objects.filter(id=workflowId).delete()
        res.update(True, "Workflow deleted successfully")
        return res

    @staticmethod
    def getWorkflowRuns(workflowId: int, offset: int):
        """
        Service to fetch and serialize workflows runs
        :param workflowId: id of Workflows.Workflow
        """
        LIMIT = 10
        res = ApiResponse(message="Error in retrieving workflow logs")
        workflowRuns = WorkflowRun.objects.filter(workflow=workflowId).order_by("-id")
        total = workflowRuns.count()
        data = WorkflowRunSerializer(workflowRuns[offset:offset+LIMIT], many=True).data

        res.update(
            True,
            "WorkflowRuns retrieved successfully",
            {"total": total, "workflowRuns": data},
        )
        return res

    @staticmethod
    def getWorkflowRunLogs(workflowRunId: int):
        """
        Service to fetch logs related to given workflowRun
        :param workflowRunId: if of model workflows.workflowRun
        """
        res = ApiResponse(message="Error in retrieving workflow logs")
        workflowRun = WorkflowRun.objects.get(id=workflowRunId)
        total = []
        res.update(
            True,
            "WorkflowRuns retrieved successfully",
            {"total": total, "workflowRunLogs": []},
        )
        return res

    @staticmethod
    def updateTriggerWorkflow(workflowId: int, triggerWorkflowId: int, triggerWorkflowStatus: int):
        """Update given workflow's trigger workflow"""
        res = ApiResponse(message="Error in updating trigger workflow")
        updateStatus = Workflow.objects.filter(id=workflowId).update(triggerWorkflow_id=triggerWorkflowId, triggerWorkflowStatus=triggerWorkflowStatus)
        res.update(True, "Trigger workflow updated successfully", updateStatus)
        return res

    @staticmethod
    def updateSchedule(workflowId: int, scheduleId: int):
        """Update given workflow's schedule"""
        res = ApiResponse(message="Error in updating workflow schedule")
        workflow = Workflow.objects.filter(id=workflowId).first()
        if scheduleId and workflow.periodictask is not None:
            workflow.periodictask.crontab_id=scheduleId
            workflow.periodictask.save()
        elif scheduleId and workflow.periodictask is None:
            periodictask = PeriodicTask.objects.create(
                crontab_id=scheduleId,
                name=workflow.name,
                task="workflows.tasks.runWorkflowJob",
                args = str([workflow.id])
            )
            workflow.periodictask = periodictask
            workflow.save()
        else:
            PeriodicTask.objects.get(id=workflow.periodictask.id).delete()
            workflow.periodictask = None
            workflow.save()
        res.update(True, "Workflow schedule updated successfully", True)
        return res


class WorkflowActions:
    @staticmethod
    def runWorkflow(workflowId: int):
        """
        Runs given workflow
        """
        from workflows.tasks import runWorkflowJob

        res = ApiResponse(message="Error in running workflow")

        existingWorkflows = WorkflowRun.objects.filter(workflow_id=workflowId).order_by(
            "-startTimestamp"
        )
        if existingWorkflows.count() and existingWorkflows[0].status in [
            STATUS_RUNNING,
            STATUS_QUEUED,
        ]:
            res.update(False, "Can't run already running workflow")
            return res

        workflowRun = WorkflowRun.objects.create(
            workflow_id=workflowId, status=STATUS_QUEUED
        )
        runWorkflowJob.delay(workflowId=workflowId, workflowRunId=workflowRun.id)
        res.update(True, "Ran workflow successfully")
        return res

    @staticmethod
    def stopWorkflow(workflowRunId: int):
        """
        Stops given workflow
        """
        res = ApiResponse(message="Error in stopping workflow")
        
        # Stopping workflow task
        workflowRun = WorkflowRun.objects.get(id=workflowRunId)
        # Revoke celery task
        app.control.revoke(workflowRun.taskId, terminate=True)
        # Update workflow run status
        workflowRun.status = STATUS_ABORTED
        workflowRun.endTimestamp = dt.datetime.now()
        workflowRun.save()

        # Stopping notebook tasks
        notebookRunStatuses = RunStatus.objects.filter(workflowRun=workflowRunId)
        for notebookRunStatus in notebookRunStatuses:
            if notebookRunStatus.status == NOTEBOOK_STATUS_QUEUED:
                app.control.revoke(notebookRunStatus.taskId, terminate=True)
                notebookRunStatus.status = NOTEBOOK_STATUS_ABORT
                notebookRunStatus.save()
            elif notebookRunStatus.status == NOTEBOOK_STATUS_RUNNING:
                notebookRunStatus.status = NOTEBOOK_STATUS_ABORT
                notebookRunStatus.save()
                NotebookJobServices.stopNotebookJob(notebookRunStatus.notebookId)

        res.update(True, "Stopped workflow successfully")
        return res
