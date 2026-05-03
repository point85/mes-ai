import unittest
from copy import deepcopy

from datetime import datetime, date, time, timedelta
from PyShift.workschedule.shift_utils import ShiftUtils

##
# Base class for testing shift plans
# 
class BaseTest(unittest.TestCase):     
    def setUp(self):
        # work workSchedule
        self.workSchedule = None
    
        # reference date for start of shift rotations
        self.referenceDate = date(2016, 10, 31)
        
        # a later date
        self.laterDate = date(2021, 10, 1)
        self.laterTime = time(7, 0, 0)

        self.testObjectDeletions = True

    def shiftTests(self): 
        self.assertTrue(len(self.workSchedule.shifts) > 0)

        for shift in self.workSchedule.shifts: 
            total = shift.duration
            start = shift.startTime
            end = shift.getEndTime()

            self.assertTrue(len(shift.name) > 0)
            self.assertTrue(len(shift.description) > 0)

            self.assertTrue(total.total_seconds() > 0)
            self.assertTrue(shift.breaks is not None)
            self.assertTrue(start is not None)
            self.assertTrue(end is not None)

            worked = None
            spansMidnight = shift.spansMidnight()
            
            if (spansMidnight): 
                # get the interval before midnight
                worked = shift.calculateTotalWorkingTime(start, end, True)
            else:
                worked = shift.calculateWorkingTime(start, end)

            self.assertTrue(worked == total)

            if (spansMidnight): 
                worked = shift.calculateTotalWorkingTime(start, start, True)
            else: 
                worked = shift.calculateWorkingTime(start, start)

            # 24 hour shift on midnight is a special case
            if (total.total_seconds() == 86400): 
                self.assertTrue(worked.total_seconds() == 86400)
            else: 
                self.assertTrue(worked.total_seconds() == 0)

            if (spansMidnight): 
                worked = shift.calculateTotalWorkingTime(end, end, True)
            else: 
                worked = shift.calculateWorkingTime(end, end)

            if (total.total_seconds() == 86400): 
                self.assertTrue(worked.total_seconds() == 86400)
            else: 
                self.assertTrue(worked.total_seconds() == 0)

            try: 
                dt = datetime(1970,1,1,hour=start.hour, minute=start.minute, second=start.second) - timedelta(minutes=1)
                worked = shift.calculateWorkingTime(dt.time(), end)

                if (total != shift.duration):
                    self.fail("Bad working time")
    
            except:
                # expected
                pass

            try: 
                dt = datetime(1970,1,1,hour=end.hour, minute=end.minute, second=end.second) + timedelta(minutes=1)
                worked = shift.calculateWorkingTime(start, dt.time())
                if (total != shift.duration): 
                    self.fail("Bad working time")
    
            except:
                # expected
                pass
            
    def teamTests(self, hoursPerRotation, rotationDays): 
        self.assertTrue(len(self.workSchedule.teams) > 0)

        for team in self.workSchedule.teams:
            self.assertTrue(len(team.name) > 0)
            self.assertTrue(len(team.description) > 0)
            self.assertTrue(team.getDayInRotation(team.rotationStart) == 1)
            hours = team.rotation.getWorkingTime()
            self.assertTrue(hours == hoursPerRotation)
            self.assertTrue(team.getPercentageWorked() > 0.0)
            self.assertTrue(team.getRotationDuration() == rotationDays)
            self.assertTrue(team.rotationStart is not None)

            rotation = team.rotation
            self.assertTrue(rotation.getDuration() == rotationDays)
            self.assertTrue(len(rotation.periods) > 0)
            self.assertTrue(rotation.getWorkingTime().total_seconds() <= rotation.getDuration().total_seconds())

        self.assertTrue(self.workSchedule.nonWorkingPeriods is not None)

    def shiftInstanceTests(self, beginDate): 
        ONE_DAY = timedelta(days=1)
        
        rotation = self.workSchedule.teams[0].rotation

        # shift instances
        startDate = beginDate
        endDate = beginDate + rotation.getDuration()

        days = ShiftUtils.toEpochDay(endDate) - ShiftUtils.toEpochDay(self.referenceDate) + 1
        day = startDate

        for _i in range(days):
            instances = self.workSchedule.getShiftInstancesForDay(day)

            for instance in instances:
                self.assertTrue(instance.startDateTime < instance.getEndTime())
                self.assertTrue(instance.shift is not None)
                self.assertTrue(instance.team is not None)

                shift = instance.shift
                startTime = shift.startTime
                endTime = shift.getEndTime()

                self.assertTrue(shift.isInShift(startTime))
                
                delta = datetime(1970,1,1,hour=startTime.hour, minute=startTime.minute, second=startTime.second) + timedelta(seconds=1)
                self.assertTrue(shift.isInShift(delta.time()))

                shiftDuration = instance.shift.duration

                # midnight is special case
                if (shiftDuration != timedelta(hours=24)): 
                    delta = datetime(1970,1,1,hour=startTime.hour, minute=startTime.minute, second=startTime.second) - timedelta(seconds=1)
                    self.assertFalse(shift.isInShift(delta.time()))
    

                self.assertTrue(shift.isInShift(endTime))
                delta = datetime(1970,1,1,hour=endTime.hour, minute=endTime.minute, second=endTime.second) - timedelta(seconds=1)
                self.assertTrue(shift.isInShift(delta.time()))

                if (shiftDuration != ONE_DAY):
                    delta = datetime(1970,1,1,hour=endTime.hour, minute=endTime.minute, second=endTime.second) + timedelta(seconds=1)
                    self.assertFalse(shift.isInShift(delta.time()))
    
                ldt = datetime.combine(day, startTime)
                self.assertTrue(len(self.workSchedule.getShiftInstancesForTime(ldt))> 0)

                delta = datetime(1970,1,1,hour=startTime.hour, minute=startTime.minute, second=startTime.second) + timedelta(seconds=1)
                ldt = datetime.combine(day, delta.time())
                self.assertTrue(len(self.workSchedule.getShiftInstancesForTime(ldt))> 0)

                delta = datetime(1970,1,1,hour=startTime.hour, minute=startTime.minute, second=startTime.second) - timedelta(seconds=1)
                ldt = datetime.combine(day, delta.time())

                for si in self.workSchedule.getShiftInstancesForTime(ldt):
                    if (shiftDuration != timedelta(hours=24)): 
                        self.assertFalse(shift.name == si.shift.name)

                ldt = datetime.combine(day, endTime)
                self.assertTrue(len(self.workSchedule.getShiftInstancesForTime(ldt))> 0)

                delta = datetime(1970,1,1,hour=endTime.hour, minute=endTime.minute, second=endTime.second) - timedelta(seconds=1)
                ldt = datetime.combine(day, delta.time())
                self.assertTrue(len(self.workSchedule.getShiftInstancesForTime(ldt)) > 0)

                delta = datetime(1970,1,1,hour=endTime.hour, minute=endTime.minute, second=endTime.second) + timedelta(seconds=1)
                ldt = datetime.combine(day, delta.time())

                for si in self.workSchedule.getShiftInstancesForTime(ldt):
                    if (shiftDuration != ONE_DAY): 
                        self.assertFalse(shift.name == si.shift.name)
        
            day = day + ONE_DAY

    def runBaseTest(self, hoursPerRotation, rotationDays, startingDate = None): 
        beginDate = self.referenceDate
        
        if (startingDate is not None):
            beginDate = startingDate
            
        # toString
        print(str(self.workSchedule))
        end = timedelta(days=rotationDays.days)
        self.workSchedule.printShiftInstances(beginDate, beginDate + end)

        self.assertTrue(len(self.workSchedule.name) > 0)
        self.assertTrue(len(self.workSchedule.description) > 0)
        self.assertTrue(self.workSchedule.nonWorkingPeriods is not None)

        # shifts
        self.shiftTests()

        # teams
        self.teamTests(hoursPerRotation, rotationDays)

        # shift instances
        self.shiftInstanceTests(beginDate)

        # deletions 
        self.deletionTests()

    def deletionTests(self): 
        if (self.workSchedule is None):
            return 
        
        # team deletions
        teams = deepcopy(self.workSchedule.teams)

        for team in teams: 
            self.workSchedule.deleteTeam(team)

        self.assertTrue(len(self.workSchedule.teams) == 0)

        # shift deletions
        shifts = deepcopy(self.workSchedule.shifts)

        for shift in shifts:
            self.workSchedule.deleteShift(shift)

        self.assertTrue(len(self.workSchedule.shifts) == 0)

        # non-working period deletions
        periods = deepcopy(self.workSchedule.nonWorkingPeriods)

        for period in periods:
            self.workSchedule.deleteNonWorkingPeriod(period)

        self.assertTrue(len(self.workSchedule.nonWorkingPeriods) == 0)
