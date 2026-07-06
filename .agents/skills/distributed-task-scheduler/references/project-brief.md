# Project Brief

This reference is derived from the project presentation files:

- `C:/Users/SHASHANK/Downloads/Presentationformat (3).pdf`
- `C:/Users/SHASHANK/Downloads/Presentationformat (3).pptx`

## Goal

Build an end-to-end distributed task scheduler that supports:

- immediate jobs
- future-dated jobs
- cron-based recurring jobs

The system should remain available under failure, scale horizontally, and keep execution latency low.

## Problem Statement

The presentation frames the main challenge as reliably handling large volumes of distributed tasks while avoiding:

- single points of failure from single-node schedulers
- lost work when workers crash during execution
- poor throughput on one machine
- limited real-time visibility into job state

## Objectives

- Support 5,000 jobs per second
- Aim for under 2 seconds execution latency
- Deliver at-least-once execution
- Provide real-time status monitoring
- Expose cancel and runNow APIs

## Functional Requirements

- Create and schedule jobs
- Handle immediate, future, and cron jobs
- Monitor job status in real time
- Update or cancel jobs
- Trigger jobs immediately through a runNow flow

## Non-Functional Requirements

- Availability over consistency
- Fault tolerance with retries
- Horizontal scalability
- Durable tracking of execution state

## Core Entities

- Job
- Scheduler
- Executor

## Future Scope

- DAG support for dependent jobs
- Multi-tenancy
- Priority queuing
- Web dashboard with monitoring and alerts
