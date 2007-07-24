#!/usr/bin/env python2.4

from base.prototype import JobSubmissionEvent, JobTerminationEvent, JobPredictionIsOverEvent
from base.prototype import ValidatingMachine
from base.event_queue import EventQueue
from common import CpuSnapshot, list_print
from easy_plus_plus_scheduler import EasyPlusPlusScheduler

import sys

class Simulator(object):
    """
    Assumption 1: The simulation clock goes only forward. Specifically,
    an event on time t can only produce future events with time t' = t or t' > t.
    Assumption 2: self.jobs holds every job that was introduced to the simulation.
    """

    def __init__(self, jobs, num_processors, scheduler):
        self.num_processors = num_processors
        self.jobs = jobs
        self.terminated_jobs=[]
        self.scheduler = scheduler

        self.event_queue = EventQueue()

        self.machine = ValidatingMachine(num_processors=num_processors, event_queue=self.event_queue)

        self.event_queue.add_handler(JobSubmissionEvent, self.handle_submission_event)
        self.event_queue.add_handler(JobTerminationEvent, self.handle_termination_event)
        if isinstance(scheduler, EasyPlusPlusScheduler):
            self.event_queue.add_handler(JobPredictionIsOverEvent, self.handle_prediction_event)
            

        for job in self.jobs:
            self.event_queue.add_event( JobSubmissionEvent(job.submit_time, job) )

    def handle_submission_event(self, event):
        assert isinstance(event, JobSubmissionEvent)
        newEvents = self.scheduler.new_events_on_job_submission(event.job, event.timestamp)
        for event in newEvents:
            self.event_queue.add_event(event)

    def handle_termination_event(self, event):
        assert isinstance(event, JobTerminationEvent)
        newEvents = self.scheduler.new_events_on_job_termination(event.job, event.timestamp)
        self.terminated_jobs.append(event.job)
        for event in newEvents:
            self.event_queue.add_event(event)

    def handle_prediction_event(self, event):
        assert isinstance(event, JobPredictionIsOverEvent)
        newEvents = self.scheduler.new_events_on_job_under_prediction(event.job, event.timestamp)
        for event in newEvents:
            self.event_queue.add_event(event)

            
    def run(self):
        while not self.event_queue.is_empty:
            self.event_queue.advance()

def run_simulator(num_processors, jobs, scheduler):
    simulator = Simulator(jobs, num_processors, scheduler)
    simulator.run()
    print_simulator_stats(simulator)
    return simulator

def print_simulator_stats(simulator):
    simulator.scheduler.cpu_snapshot._restore_old_slices()
    # simulator.scheduler.cpu_snapshot.printCpuSlices()
    print_statistics(simulator.terminated_jobs)
    
def print_statistics(jobs):
    assert jobs is not None, "Input file is probably empty"
    
    sigma_slowdowns = sigma_bounded_slowdowns = 0.0
    counter = 0

    for job in jobs:

        counter += 1

        wait_time = float(job.start_to_run_at_time - job.submit_time)
        run_time  = float(job.actual_run_time)

        sigma_slowdowns += (wait_time + run_time) / run_time

        if run_time > 10:
            sigma_bounded_slowdowns += (wait_time + run_time) / run_time
        else:
            sigma_bounded_slowdowns += (wait_time + run_time) / 10


    print
    print "STATISTICS: "
    print "Average slowdown: ", float(sigma_slowdowns / counter)
    print "Average bounded slowdown: ", float(sigma_bounded_slowdowns / counter) 
    print "Number of jobs: ", counter

