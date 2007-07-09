from common import Scheduler, CpuSnapshot, list_copy
from base.prototype import JobStartEvent



sjf_sort_key = (
    lambda job :  job.predicted_run_time
)



class  EasyPlusPlusScheduler(Scheduler):
    """ This algorithm implements the algorithm in the paper of Tsafrir, Etzion, Feitelson, june 2007?
    """
    
    def __init__(self, num_processors):
        super(EasyPlusPlusScheduler, self).__init__(num_processors)
        self.cpu_snapshot = CpuSnapshot(num_processors)
        self.unscheduled_jobs = []

        self.user_run_time_prev = {}
        self.user_run_time_last = {}

    
    def new_events_on_job_submission(self, just_submitted_job, current_time):
	print ">>>>>>>>>>>>>>>>> Arrival event"
	self.cpu_snapshot.printCpuSlices()

        u_id = str(just_submitted_job.user_id)
        if not self.user_run_time_last.has_key(u_id): 
            self.user_run_time_prev[u_id] = None 
            self.user_run_time_last[u_id] = None
        self.cpu_snapshot.archive_old_slices(current_time)
        self.unscheduled_jobs.append(just_submitted_job)
        return [
            JobStartEvent(current_time, job)
            for job in self._schedule_jobs(current_time)
        ]

    def new_events_on_job_termination(self, job, current_time):
	print ">>>>>>>>>>>>>>>>> Termination event"
	self.cpu_snapshot.printCpuSlices()

        self.user_run_time_prev[job.user_id]  = self.user_run_time_last[job.user_id]
        self.user_run_time_last[job.user_id]  = job.actual_run_time
        print self.user_run_time_last
        self.cpu_snapshot.archive_old_slices(current_time)
        self.cpu_snapshot.delTailofJobFromCpuSlices(job)
        return [
            JobStartEvent(current_time, job)
            for job in self._schedule_jobs(current_time)
        ]


    def new_events_on_job_under_prediction(self, job, current_time):
	print "<<<<<<<<<<<<<<<< Prediction event"
	self.cpu_snapshot.printCpuSlices()

        assert job.prediction_run_time <= job.user_estimated_run_time
        self.cpu_snapshot.assignTailofJobToTheCpuSlices(job)
        return []


    def _schedule_jobs(self, current_time):
        "Schedules jobs that can run right now, and returns them"
        for job in self.unscheduled_jobs:
            u_id = str(job.user_id)
            if self.user_run_time_prev[u_id] is not None and self.user_run_time_last[u_id] is not None: 
                average =  int((self.user_run_time_last[u_id] + self.user_run_time_prev[u_id])/ 2)
                job.prediction_run_time = min (job.user_estimated_run_time, average)

        jobs  = self._schedule_head_of_list(current_time)
        jobs += self._backfill_jobs(current_time)
        return jobs


    def _schedule_head_of_list(self, current_time):     
        result = []
        while True:
            if len(self.unscheduled_jobs) == 0:
                break
            # Try to schedule the first job
            if self.cpu_snapshot.free_processors_available_at(current_time) >= self.unscheduled_jobs[0].num_required_processors:
                job = self.unscheduled_jobs.pop(0)
                self.cpu_snapshot.assignJob(job, current_time)
                result.append(job)
            else:
                # first job can't be scheduled
                break
        return result
    

    def _backfill_jobs(self, current_time):
        "Overriding parent method"
        if len(self.unscheduled_jobs) <= 1:
            return []

        result = []  
        first_job = self.unscheduled_jobs[0]        
        tail =  list_copy(self.unscheduled_jobs[1:])
        tail_of_jobs_by_sjf_order = sorted(tail, key=sjf_sort_key)
        
        self.cpu_snapshot.assignJobEarliest(first_job, current_time)
        
        for job in tail_of_jobs_by_sjf_order:
            if self.cpu_snapshot.canJobStartNow(job, current_time): 
                self.unscheduled_jobs.remove(job)
                self.cpu_snapshot.assignJob(job, current_time)
                result.append(job)
                
        self.cpu_snapshot.delJobFromCpuSlices(first_job)

        return result



