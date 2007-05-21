from common  import *
from events import *

class EasyBackfillScheduler(Scheduler):
    
    def __init__(self, total_nodes = 100):
        self.cpu_snapshot = CpuSnapshot(total_nodes)
        self.waiting_list_of_unscheduled_jobs = []
        
    def handleArrivalOfJobEvent(self, just_arrived_job, current_time):
        """ Here we first add the new job to the waiting list. We then try to schedule
        the jobs in the waiting list, returning a collection of new termination events """
        self.cpu_snapshot.archive_old_slices(current_time)
        self.waiting_list_of_unscheduled_jobs.append(just_arrived_job)
        newEvents = Events()
        if len(self.waiting_list_of_unscheduled_jobs) == 1:  
            start_time = self.cpu_snapshot.jobEarliestAssignment(just_arrived_job, current_time)
            if start_time == current_time:
                self.waiting_list_of_unscheduled_jobs = []
                self.cpu_snapshot.assignJob(just_arrived_job, current_time)
                termination_time = current_time + just_arrived_job.actual_duration
                newEvents.add_job_termination_event(termination_time, just_arrived_job) 
        else: # there are at least 2 jobs in the waiting list  
            first_job = self.waiting_list_of_unscheduled_jobs[0]
            if self.canBeBackfilled(first_job, just_arrived_job, current_time):
                    self.waiting_list_of_unscheduled_jobs.pop()
                    self.cpu_snapshot.assignJob(just_arrived_job, current_time)
                    termination_time = current_time + just_arrived_job.actual_duration
                    newEvents.add_job_termination_event(termination_time, just_arrived_job)                                
        return newEvents

    def handleTerminationOfJobEvent(self, job, current_time):
        """ Here we first delete the tail of the just terminated job (in case it's
        done before user estimation time). We then try to schedule the jobs in the waiting list,
        returning a collection of new termination events """
        self.cpu_snapshot.archive_old_slices(current_time)
        self.cpu_snapshot.delTailofJobFromCpuSlices(job)
        return self._schedule_jobs(current_time)
    
    def _schedule_jobs(self, current_time):       
        newEvents = Events()
        if len(self.waiting_list_of_unscheduled_jobs) == 0:
            return newEvents
        self._schedule_the_head_of_the_waiting_list(current_time, newEvents)
        self._backfill_the_tail_of_the_waiting_list(current_time, newEvents)
        return newEvents

    def _schedule_the_head_of_the_waiting_list(self, time, newEvents):
        while len(self.waiting_list_of_unscheduled_jobs) > 0: 
            first_job = self.waiting_list_of_unscheduled_jobs[0]
            start_time_of_first_job = self.cpu_snapshot.jobEarliestAssignment(first_job, time)
            if start_time_of_first_job == time:
                self.waiting_list_of_unscheduled_jobs.remove(first_job)
                self.cpu_snapshot.assignJob(first_job, time)
                termination_time = time + first_job.actual_duration
                newEvents.add_job_termination_event(termination_time, first_job) 
            else:
                break

    def _backfill_the_tail_of_the_waiting_list(self, time, newEvents):
        if len(self.waiting_list_of_unscheduled_jobs) > 1:
            first_job = self.waiting_list_of_unscheduled_jobs[0]
            for next_job in self.waiting_list_of_unscheduled_jobs[1:] : 
                if self.canBeBackfilled(first_job, next_job, time):
                    self.waiting_list_of_unscheduled_jobs.remove(next_job)
                    self.cpu_snapshot.assignJob(next_job, time)
                    termination_time = time + next_job.actual_duration
                    newEvents.add_job_termination_event(termination_time, next_job)

    def canBeBackfilled(self, first_job, second_job, time):
        start_time_of_second_job = self.cpu_snapshot.jobEarliestAssignment(second_job, time)

        if start_time_of_second_job > time:
            return False

        shadow_time = self.cpu_snapshot.jobEarliestAssignment(first_job, time)
        self.cpu_snapshot.assignJob(second_job, time)
        start_time_of_1st_if_2nd_job_assigned = self.cpu_snapshot.jobEarliestAssignment(first_job, time)
        
        self.cpu_snapshot.delJobFromCpuSlices(second_job)
       
        if start_time_of_1st_if_2nd_job_assigned > shadow_time:
            return False 
        else:
            return True 
      