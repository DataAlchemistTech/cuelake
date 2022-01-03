<p align="center">
  <a href="https://cuelake.cuebook.ai" target="_blank">
    <img alt="Cuelake Logo" width="220" src="docs/images/cuelake.png">
  </a>
</p>
<p align="center">
  <a href="https://codeclimate.com/github/cuebook/cuelake/maintainability">
    <img src="https://api.codeclimate.com/v1/badges/db3c4c0355e11d23bb66/maintainability" alt="Maintainability">
  </a>
  <a href="https://codeclimate.com/github/cuebook/cuelake/test_coverage">
    <img src="https://api.codeclimate.com/v1/badges/db3c4c0355e11d23bb66/test_coverage" alt="Test Coverage">
  </a>
  <a href="https://github.com/cuebook/cuelake/actions/workflows/pr_checks.yml">
    <img src="https://github.com/cuebook/cuelake/actions/workflows/pr_checks.yml/badge.svg" alt="PR Checks">
  </a>
  <br>
  <a href="https://github.com/cuebook/cuelake/blob/main/LICENSE.md">
    <img src="https://img.shields.io/github/license/cuebook/cuelake" alt="License">
  </a>
  <a href="https://discord.gg/R7EABXwUnv">
    <img src="https://discordapp.com/api/guilds/854395659431182366/widget.png" alt="Discord">
  </a>
  <a href="https://hub.docker.com/r/cuebook/lakehouse/tags">
    <img src="https://img.shields.io/docker/pulls/cuebook/lakehouse" alt="Docker Pulls">
  </a>
</p>
<br>
<br>

With CueLake, you can use SQL to build `ELT` (Extract, Load, Transform) pipelines on a **data lakehouse**.

You write **Spark SQL** statements in **Zeppelin** notebooks. You then schedule these notebooks using workflows (DAGs).

To extract and load incremental data, you write simple select statements. CueLake executes these statements against your databases and then merges incremental data into your data lakehouse (powered by **Apache Iceberg**).

To transform data, you write SQL statements to create views and tables in your data lakehouse. 

CueLake uses Celery as the executor and celery-beat as the scheduler. Celery jobs trigger **Zeppelin** notebooks. Zeppelin auto-starts and stops the Spark cluster for every scheduled run of notebooks.

To know why we are building CueLake, read our [viewpoint](https://cuelake.cuebook.ai/viewpoint).


![CueLake](docs/images/CueLake.gif)


# Getting started
CueLake uses Kubernetes `kubectl` for installation. Create a namespace and then install using the `cuelake.yaml` file. Creating a namespace is optional. You can install in the default namespace or in any existing namespace.

In the commands below, we use `cuelake` as the namespace.
```
kubectl create namespace cuelake
kubectl apply -f https://raw.githubusercontent.com/cuebook/cuelake/main/cuelake.yaml -n cuelake
kubectl port-forward services/lakehouse 8080:80 -n cuelake
```

Now visit [http://localhost:8080](http://localhost:8080) in your browser.

If you don’t want to use Kubernetes and instead want to try it out on your local machine first, we’ll soon have a docker-compose version. Let us know if you’d want that sooner.

# Features
* **Upsert Incremental data.** CueLake uses Iceberg’s `merge into` query to automatically merge incremental data.
* **Create Views in data lakehouse.** CueLake enables you to create views over Iceberg tables.
* **Create DAGs.** Group notebooks into workflows and create DAGs of these workflows.  
* **Elastically Scale Cloud Infrastructure.** CueLake uses Zeppelin to auto create and delete Kubernetes resources required to run data pipelines.
* **In-built Scheduler** to schedule your pipelines.
* **Automated maintenance of Iceberg tables.** CueLake does automated maintenance of Iceberg tables -  expires snapshots, removes old metadata and orphan files, compacts data files.
* **Monitoring.**  Get Slack alerts when a pipeline fails. CueLake maintains detailed logs.
* **Versioning in Github.** Commit and maintain versions of your Zeppelin notebooks in Github.
* **Data Security.** Your data always stays within your cloud account.

### Current Limitations
* Supports AWS S3 as a destination. Support for ADLS and GCS is in the roadmap.
* Uses Apache Iceberg as an open table format. Delta support is in the roadmap.
* Uses Celery for scheduling jobs. Support for Airflow is in the roadmap.

# Support
For general help using CueLake, read the [documentation](https://cuelake.cuebook.ai/), or go to [Github Discussions](https://github.com/cuebook/cuelake/discussions).

To report a bug or request a feature, open an [issue](https://github.com/cuebook/cuelake/issues).

# Contributing
We'd love contributions to CueLake. Before you contribute, please first discuss the change you wish to make via an [issue](https://github.com/cuebook/cuelake/issues) or a [discussion](https://github.com/cuebook/cuelake/discussions). Contributors are expected to adhere to our [code of conduct](https://github.com/cuebook/cuelake/blob/main/CODE_OF_CONDUCT.md).
