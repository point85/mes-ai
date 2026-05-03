from datetime import datetime, date, time, timedelta
from tests.unit.pyshift_base_test import BaseTest
from PyShift.workschedule.work_schedule import WorkSchedule
from PyShift.workschedule.shift import Shift
from PyShift.workschedule.rotation import Rotation, RotationSegment
from PyShift.workschedule.team import Team
from PyShift.workschedule.team_member import TeamMember, TeamMemberException

class TestWorkSchedule(BaseTest):
    def testTeamWorkingTime2(self):
        self.workSchedule = WorkSchedule("4 Team Plan", "test schedule")

        # Day shift #1, starts at 07:00 for 15.5 hours
        crossover = self.workSchedule.createShift("Crossover", "Day shift #1 cross-over", time(7, 0, 0),
            timedelta(hours=15, minutes=30))

        # Day shift #2, starts at 07:00 for 14 hours
        day = self.workSchedule.createShift("Day", "Day shift #2", time(7, 0, 0), timedelta(hours=14))

        # Night shift, starts at 22:00 for 14 hours
        night = self.workSchedule.createShift("Night", "Night shift", time(22, 0, 0), timedelta(hours=14))

        # Team 4-day rotation
        rotation = self.workSchedule.createRotation("4 Team", "4 Team")
        rotation.addSegment(day, 1, 0)
        rotation.addSegment(crossover, 1, 0)
        rotation.addSegment(night, 1, 1)

        team1 = self.workSchedule.createTeam("Team 1", "First team", rotation, self.referenceDate)

        # partial in Day 1
        am7 = time(7, 0, 0)
        testStart = self.referenceDate + timedelta(days=rotation.getDayCount())
        fromDateTime = datetime.combine(testStart, am7)
        toDateTime = datetime.combine(testStart, time(hour=am7.hour+1))
        
        duration = team1.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=1))

        fromDateTime = datetime.combine(testStart, time.min)
        toDateTime = datetime.combine(testStart, time.max)

        duration = team1.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=14))

        toDateTime = datetime.combine(testStart, time.max) + timedelta(days=1)
        duration = team1.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=29, minutes=30))

        toDateTime = datetime.combine(testStart, time.max) + timedelta(days=2)
        duration = team1.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=31, minutes=30))

        toDateTime = datetime.combine(testStart, time.max) + timedelta(days=3)
        duration = team1.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=43, minutes=30))

        toDateTime = datetime.combine(testStart, time.max) + timedelta(days=4)
        duration = team1.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=57, minutes=30))

        toDateTime = datetime.combine(testStart, time.max) + timedelta(days=5)
        duration = team1.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=73))

        toDateTime = datetime.combine(testStart, time.max) + timedelta(days=6)
        duration = team1.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=75))

        toDateTime = datetime.combine(testStart, time.max) + timedelta(days=7)
        duration = team1.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=87))

        # from third day in rotation for Team1
        fromDateTime = datetime.combine(testStart, time.min) + timedelta(days=2)
        toDateTime = datetime.combine(testStart, time.max) + timedelta(days=2)
        duration = team1.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=2))

        toDateTime = datetime.combine(testStart, time.max) + timedelta(days=3)
        duration = team1.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=14))

        toDateTime = datetime.combine(testStart, time.max) + timedelta(days=4)
        duration = team1.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=28))

        toDateTime = datetime.combine(testStart, time.max) + timedelta(days=5)
        duration = team1.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=43, minutes=30))

        toDateTime = datetime.combine(testStart, time.max) + timedelta(days=6)
        duration = team1.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=45, minutes=30))
    
    
    def testGenericShift(self):
        # regular work week with holidays and breaks
        self.workSchedule = WorkSchedule("Regular 40 hour work week", "9 to 5")

        # holidays
        memorialDay = self.workSchedule.createNonWorkingPeriod("MEMORIAL DAY", "Memorial day",
            datetime.combine(date(2016, 5, 30), time(0, 0, 0)), timedelta(hours=24))
        self.workSchedule.createNonWorkingPeriod("INDEPENDENCE DAY", "Independence day", 
            datetime.combine(date(2016, 7, 4), time(0, 0, 0)), timedelta(hours=24))
        self.workSchedule.createNonWorkingPeriod("LABOR DAY", "Labor day", 
            datetime.combine(date(2016, 9, 5), time(0, 0, 0)), timedelta(hours=24))
        self.workSchedule.createNonWorkingPeriod("THANKSGIVING", "Thanksgiving day and day after",
            datetime.combine(date(2016, 11, 24), time(0, 0, 0)), timedelta(hours=48))
        self.workSchedule.createNonWorkingPeriod("CHRISTMAS SHUTDOWN", "Christmas week scheduled maintenance",
            datetime.combine(date(2016, 12, 25), time(0, 30, 0)), timedelta(hours=168))

        # each shift duration
        shiftDuration = timedelta(hours=8)
        shift1Start = time(7, 0, 0)
        shift2Start = time(15, 0, 0)

        # shift 1
        shift1 = self.workSchedule.createShift("Shift1", "Shift #1", shift1Start, shiftDuration)

        # breaks
        shift1.createBreak("10AM", "10 am break", time(10, 0, 0), timedelta(minutes=15))
        shift1.createBreak("LUNCH", "lunch", time(12, 0, 0), timedelta(hours=1))
        shift1.createBreak("2PM", "2 pm break", time(14, 0, 0), timedelta(minutes=15))

        # shift 2
        shift2 = self.workSchedule.createShift("Shift2", "Shift #2", shift2Start, shiftDuration)

        # shift 1, 5 days ON, 2 OFF
        rotation1 = self.workSchedule.createRotation("Shift1", "Shift1")
        rotation1.addSegment(shift1, 5, 2)

        # shift 2, 5 days ON, 2 OFF
        rotation2 = self.workSchedule.createRotation("Shift2", "Shift2")
        rotation2.addSegment(shift2, 5, 2)

        startRotation = date(2016, 1, 1)
        team1 = self.workSchedule.createTeam("Team1", "Team #1", rotation1, startRotation)
        team2 = self.workSchedule.createTeam("Team2", "Team #2", rotation2, startRotation)

        # same day
        fromDateTime = datetime.combine(startRotation, shift1Start) + timedelta(days=7)
        toDateTime = None

        totalWorking = None

        # 21 days, team1
        d = timedelta()

        for i in range(0, 21):
            toDateTime = fromDateTime + timedelta(days=i)
            totalWorking = team1.calculateWorkingTime(fromDateTime, toDateTime)
            rotationDay = team1.getDayInRotation(toDateTime.date())

            self.assertTrue(totalWorking == d)

            if (isinstance(rotation1.periods[rotationDay - 1], Shift)):
                d = d + shiftDuration

        totalSchedule = totalWorking

        # 21 days, team2
        fromDateTime = datetime.combine(startRotation, shift2Start) + timedelta(days=7)
        d = timedelta()

        for i in range(0, 21):
            toDateTime = fromDateTime + timedelta(days=i)
            totalWorking = team2.calculateWorkingTime(fromDateTime, toDateTime)
            rotationDay = team2.getDayInRotation(toDateTime.date())

            self.assertTrue(totalWorking == d)

            if (isinstance(rotation1.periods[rotationDay - 1], Shift)):
                d = d + shiftDuration

        totalSchedule = totalSchedule + totalWorking

        scheduleDuration = self.workSchedule.calculateWorkingTime(fromDateTime, fromDateTime + timedelta(days=21))
        nonWorkingDuration = self.workSchedule.calculateNonWorkingTime(fromDateTime, fromDateTime + timedelta(days=21))
        self.assertTrue(scheduleDuration + nonWorkingDuration == totalSchedule)

        # breaks
        allBreaks = timedelta(minutes=90)
        self.assertTrue(shift1.calculateBreakTime() == allBreaks)

        # misc
        shift3 = Shift("name", "description", time(), timedelta(hours=8))
        shift3.name = "Shift3"       
        self.assertTrue(shift3.compareName(shift3) == 0)

        segment = RotationSegment(shift3, 5, 5, None)
        segment.sequence = 1
        segment.startingShift = shift2
        segment.daysOn = 5
        segment.daysOff = 2
        self.assertTrue(segment.rotation is None)

        rotation3 = Rotation("name", "description")
        rotation3.name = "Rotation3"
        self.assertTrue(rotation3.compareName(rotation3) == 0)
        self.assertTrue(len(rotation3.rotationSegments) == 0)

        self.assertFalse(team1.isDayOff(startRotation))

        team3 = Team("name", "description", rotation3, time())
        self.assertTrue(team1.compareName(team1) == 0)
        team3.rotation = rotation1
        
        self.assertFalse(team1.compareName(team3) == 0)

        self.assertFalse(memorialDay.isInPeriod(date(2016, 1, 1)))

        self.runBaseTest(timedelta(hours=40), timedelta(days=7), date(2016, 1, 1))

    
    def testManufacturingShifts(self):
        # manufacturing company
        self.workSchedule = WorkSchedule("Manufacturing Company - four twelves",
                "Four 12 hour alternating day/night shifts")

        # day shift, start at 07:00 for 12 hours
        day = self.workSchedule.createShift("Day", "Day shift", time(7, 0, 0), timedelta(hours=12))

        # night shift, start at 19:00 for 12 hours
        night = self.workSchedule.createShift("Night", "Night shift", time(19, 0, 0), timedelta(hours=12))

        # 7 days ON, 7 OFF
        dayRotation = self.workSchedule.createRotation("Day", "Day")
        dayRotation.addSegment(day, 7, 7)

        # 7 nights ON, 7 OFF
        nightRotation = self.workSchedule.createRotation("Night", "Night")
        nightRotation.addSegment(night, 7, 7)

        self.workSchedule.createTeam("A", "A day shift", dayRotation, date(2014, 1, 2))
        self.workSchedule.createTeam("B", "B night shift", nightRotation, date(2014, 1, 2))
        self.workSchedule.createTeam("C", "C day shift", dayRotation, date(2014, 1, 9))
        self.workSchedule.createTeam("D", "D night shift", nightRotation, date(2014, 1, 9))
        
        # specific checks        
        fromDateTime = datetime.combine(self.laterDate, self.laterTime)
        toDateTime = datetime.combine(self.laterDate, self.laterTime) + timedelta(days=28)
        
        workingTime = self.workSchedule.calculateWorkingTime(fromDateTime, toDateTime)
        nonWorkingTime = self.workSchedule.calculateNonWorkingTime(fromDateTime, toDateTime)
        
        self.assertTrue(workingTime.total_seconds() == 672 * 3600)
        self.assertTrue(nonWorkingTime.total_seconds() == 0 * 3600)
        
        self.assertTrue(self.workSchedule.getRotationDuration().total_seconds() == 1344 * 3600)
        self.assertTrue(self.workSchedule.getRotationWorkingTime().total_seconds() == 336 * 3600)
        
        for team in self.workSchedule.teams:            
            self.assertTrue(team.rotation.getDuration().total_seconds() == 336 * 3600)
            self.assertAlmostEqual(team.getPercentageWorked(), 25.00, 2)
            self.assertTrue(team.rotation.getWorkingTime().total_seconds() == 84 * 3600)
            self.assertAlmostEqual(team.getAverageHoursWorkedPerWeek(), 42.0, 2)

        self.runBaseTest(timedelta(hours=84), timedelta(days=14), date(2014, 1, 9))
    
    
    def testFirefighterShifts1(self):
        # Kern Co, CA
        self.workSchedule = WorkSchedule("Kern Co.", "Three 24 hour alternating shifts")

        # shift, start 07:00 for 24 hours
        shift = self.workSchedule.createShift("24 Hour", "24 hour shift", time(7, 0, 0), timedelta(hours=24))

        # 2 days ON, 2 OFF, 2 ON, 2 OFF, 2 ON, 8 OFF
        rotation = self.workSchedule.createRotation("24 Hour", "2 days ON, 2 OFF, 2 ON, 2 OFF, 2 ON, 8 OFF")
        rotation.addSegment(shift, 2, 2)
        rotation.addSegment(shift, 2, 2)
        rotation.addSegment(shift, 2, 8)

        self.workSchedule.createTeam("Red", "A Shift", rotation, date(2017, 1, 8))
        self.workSchedule.createTeam("Black", "B Shift", rotation, date(2017, 2, 1))
        self.workSchedule.createTeam("Green", "C Shift", rotation, date(2017, 1, 2))
        
        # specific checks
        fromDateTime = datetime.combine(self.laterDate, self.laterTime)
        toDateTime = datetime.combine(self.laterDate + timedelta(days=28), self.laterTime)
        
        workingTime = self.workSchedule.calculateWorkingTime(fromDateTime, toDateTime)
        nonWorkingTime = self.workSchedule.calculateNonWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(workingTime.total_seconds() == 672 * 3600)
        self.assertTrue(nonWorkingTime.total_seconds() == 0)
        
        self.assertTrue(self.workSchedule.getRotationDuration().total_seconds() == 1296 * 3600)
        self.assertTrue(self.workSchedule.getRotationWorkingTime().total_seconds() == 432 * 3600)
        
        for team in self.workSchedule.teams:
            self.assertTrue(team.rotation.getDuration().total_seconds() == 432 * 3600)
            self.assertAlmostEqual(team.getPercentageWorked(), 33.33, 2)
            self.assertTrue(team.rotation.getWorkingTime().total_seconds() == 144 * 3600)
            self.assertAlmostEqual(team.getAverageHoursWorkedPerWeek(), 56.0, 2)


        self.runBaseTest(timedelta(hours=144), timedelta(days=18), date(2017, 2, 1))
    
    
    def testFirefighterShifts2(self):
        # Seattle, WA fire shifts
        self.workSchedule = WorkSchedule("Seattle", "Four 24 hour alternating shifts")

        # shift, start at 07:00 for 24 hours
        shift = self.workSchedule.createShift("24 Hours", "24 hour shift", time(7, 0, 0), timedelta(hours=24))

        # 1 day ON, 4 OFF, 1 ON, 2 OFF
        rotation = self.workSchedule.createRotation("24 Hours", "24 Hours")
        rotation.addSegment(shift, 1, 4)
        rotation.addSegment(shift, 1, 2)

        self.workSchedule.createTeam("A", "Platoon1", rotation, date(2014, 2, 2))
        self.workSchedule.createTeam("B", "Platoon2", rotation, date(2014, 2, 4))
        self.workSchedule.createTeam("C", "Platoon3", rotation, date(2014, 1, 31))
        self.workSchedule.createTeam("D", "Platoon4", rotation, date(2014, 1, 29))
        
        # specific checks
        fromDateTime = datetime.combine(self.laterDate, self.laterTime)
        toDateTime = datetime.combine(self.laterDate + timedelta(days=28), self.laterTime)
        
        workingTime = self.workSchedule.calculateWorkingTime(fromDateTime, toDateTime)
        nonWorkingTime = self.workSchedule.calculateNonWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(workingTime.total_seconds() == 672 * 3600)
        self.assertTrue(nonWorkingTime.total_seconds() == 0)
        
        self.assertTrue(self.workSchedule.getRotationDuration().total_seconds() == 768 * 3600)
        self.assertTrue(self.workSchedule.getRotationWorkingTime().total_seconds() == 192 * 3600)
        
        for team in self.workSchedule.teams:
            self.assertTrue(team.rotation.getDuration().total_seconds() == 192 * 3600)
            self.assertAlmostEqual(team.getPercentageWorked(), 25.00, 2)
            self.assertTrue(team.rotation.getWorkingTime().total_seconds() == 48 * 3600)
            self.assertAlmostEqual(team.getAverageHoursWorkedPerWeek(), 42.0, 2)

        self.runBaseTest(timedelta(hours=48), timedelta(days=8))

        
    def testPostalServiceShifts(self):
        # United States Postal Service
        self.workSchedule = WorkSchedule("USPS", "Six 9 hr shifts, rotating every 42 days")

        # shift, start at 08:00 for 9 hours
        day = self.workSchedule.createShift("Day", "day shift", time(8, 0, 0), timedelta(hours=9))

        rotation = self.workSchedule.createRotation("Day", "Day")
        rotation.addSegment(day, 3, 7)
        rotation.addSegment(day, 1, 7)
        rotation.addSegment(day, 1, 7)
        rotation.addSegment(day, 1, 7)
        rotation.addSegment(day, 1, 7)

        # day teams
        self.workSchedule.createTeam("Team A", "A team", rotation, self.referenceDate)
        self.workSchedule.createTeam("Team B", "B team", rotation, self.referenceDate - timedelta(days=7))
        self.workSchedule.createTeam("Team C", "C team", rotation, self.referenceDate - timedelta(days=14))
        self.workSchedule.createTeam("Team D", "D team", rotation, self.referenceDate - timedelta(days=21))
        self.workSchedule.createTeam("Team E", "E team", rotation, self.referenceDate - timedelta(days=28))
        self.workSchedule.createTeam("Team F", "F team", rotation, self.referenceDate - timedelta(days=35))
        
        # specific checks
        fromDateTime = datetime.combine(self.laterDate, self.laterTime)
        toDateTime = datetime.combine(self.laterDate + timedelta(days=28), self.laterTime)
        
        workingTime = self.workSchedule.calculateWorkingTime(fromDateTime, toDateTime)
        nonWorkingTime = self.workSchedule.calculateNonWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(workingTime.total_seconds() == 252 * 3600)
        self.assertTrue(nonWorkingTime.total_seconds() == 0)
        
        self.assertTrue(self.workSchedule.getRotationDuration().total_seconds() == 6048 * 3600)
        self.assertTrue(self.workSchedule.getRotationWorkingTime().total_seconds() == 378 * 3600)
        
        for team in self.workSchedule.teams:
            self.assertTrue(team.rotation.getDuration().total_seconds() == 1008 * 3600)
            self.assertAlmostEqual(team.getPercentageWorked(), 6.25, 2)
            self.assertTrue(team.rotation.getWorkingTime().total_seconds() == 63 * 3600)
            self.assertAlmostEqual(team.getAverageHoursWorkedPerWeek(), 10.50, 2)

        self.runBaseTest(timedelta(hours=63), timedelta(days=42))
    

    def testNursingICUShifts(self):
        # ER nursing schedule
        self.workSchedule = WorkSchedule("Nursing ICU", "Two 12 hr back-to-back shifts, rotating every 14 days")

        # day shift, starts at 06:00 for 12 hours
        day = self.workSchedule.createShift("Day", "Day shift", time(6, 0, 0), timedelta(hours=12))

        # night shift, starts at 18:00 for 12 hours
        night = self.workSchedule.createShift("Night", "Night shift", time(18, 0, 0), timedelta(hours=12))

        # day rotation
        dayRotation = self.workSchedule.createRotation("Day", "Day")
        dayRotation.addSegment(day, 3, 4)
        dayRotation.addSegment(day, 4, 3)

        # inverse day rotation (day + 3 days)
        inverseDayRotation = self.workSchedule.createRotation("Inverse Day", "Inverse Day")
        inverseDayRotation.addSegment(day, 0, 3)
        inverseDayRotation.addSegment(day, 4, 4)
        inverseDayRotation.addSegment(day, 3, 0)

        # night rotation
        nightRotation = self.workSchedule.createRotation("Night", "Night")
        nightRotation.addSegment(night, 4, 3)
        nightRotation.addSegment(night, 3, 4)

        # inverse night rotation
        inverseNightRotation = self.workSchedule.createRotation("Inverse Night", "Inverse Night")
        inverseNightRotation.addSegment(night, 0, 4)
        inverseNightRotation.addSegment(night, 3, 3)
        inverseNightRotation.addSegment(night, 4, 0)

        self.workSchedule.createTeam("A", "Day shift", dayRotation, self.referenceDate)
        self.workSchedule.createTeam("B", "Day inverse shift", inverseDayRotation, self.referenceDate)
        self.workSchedule.createTeam("C", "Night shift", nightRotation, self.referenceDate)
        self.workSchedule.createTeam("D", "Night inverse shift", inverseNightRotation, self.referenceDate)
        
        # specific checks
        fromDateTime = datetime.combine(self.laterDate, self.laterTime)
        toDateTime = datetime.combine(self.laterDate + timedelta(days=28), self.laterTime)
        
        workingTime = self.workSchedule.calculateWorkingTime(fromDateTime, toDateTime)
        nonWorkingTime = self.workSchedule.calculateNonWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(workingTime.total_seconds() == 696 * 3600)
        self.assertTrue(nonWorkingTime.total_seconds() == 0)
        
        self.assertTrue(self.workSchedule.getRotationDuration().total_seconds() == 1344 * 3600)
        self.assertTrue(self.workSchedule.getRotationWorkingTime().total_seconds() == 336 * 3600)
        
        for team in self.workSchedule.teams:
            self.assertTrue(team.rotation.getDuration().total_seconds() == 336 * 3600)
            self.assertAlmostEqual(team.getPercentageWorked(), 25.00, 2)
            self.assertTrue(team.rotation.getWorkingTime().total_seconds() == 84 * 3600)
            self.assertAlmostEqual(team.getAverageHoursWorkedPerWeek(), 42.0, 2)

        self.runBaseTest(timedelta(hours=84), timedelta(days=14))

  
    def testExceptions(self):
        self.workSchedule = WorkSchedule("Exceptions", "Test exceptions")
        shiftDuration = timedelta(hours=24)
        shiftStart = time(7, 0, 0)
        shift = self.workSchedule.createShift("Test", "Test shift", shiftStart, shiftDuration)
        startDateTime = datetime.combine(date(2017, 1, 1), time(0, 0, 0))
        period = self.workSchedule.createNonWorkingPeriod("Non-working", "Non-working period", startDateTime, timedelta(hours=24))
    
        try:
            period.setDuration(timedelta(seconds=0))
            self.self.fail()
        except Exception as e:
            # expected
            print(str(e))
    
        try:
            period.setStartDateTime(None)
            self.fail()
        except Exception as e:
            # expected
            print(str(e))

        try:
            # same period
            self.workSchedule.createNonWorkingPeriod("Non-working", "Non-working period",
                datetime.combine(date(2017, 1, 1), time(0, 0, 0)), timedelta(hours=24))
            self.fail()
        except Exception as e:
            # expected
            print(str(e))

        try:
            # crosses midnight
            endToday = datetime.combine(datetime.today(), shift.getEndTime())
            tomorrow = endToday +  timedelta(hours=1)
            shift.calculateWorkingTime(time(shiftStart.hour-1), tomorrow.time())
            self.fail()
        except Exception as e:
            # expected
            print(str(e))

        try:
            shift.setDuration(None)
            self.fail()
        except Exception as e:
            # expected
            print(str(e))

        try:
            shift.setDuration(timedelta(seconds=0))
            self.fail()
        except Exception as e:
            # expected
            print(str(e))

        try:
            shift.setDuration(timedelta(seconds=48*3600))
            self.fail()
        except Exception as e:
            # expected
            print(str(e))

        try:
            # same shift
            self.workSchedule.createShift("Test", "Test shift", shiftStart, shiftDuration)
            self.fail()
        except Exception as e:
            # expected
            print(str(e))       

        rotation = self.workSchedule.createRotation("Rotation", "Rotation")
        rotation.addSegment(shift, 5, 2)

        startRotation = date(2016, 12, 31)
        team = self.workSchedule.createTeam("Team", "Team", rotation, startRotation)

        # ok
        fromDateTime = datetime.combine(date(2017, 1, 1), time(7, 0, 0))
        toDateTime   = datetime.combine(date(2017, 2, 1), time(0, 0, 0))
                                      
        self.workSchedule.calculateWorkingTime(fromDateTime, toDateTime)
    
        try:
            # end before start
            fromDateTime = datetime.combine(date(2017, 1, 2), time(0, 0, 0))
            toDateTime   = datetime.combine(date(2017, 1, 1), time(0, 0, 0))
            self.workSchedule.calculateWorkingTime(fromDateTime, toDateTime)
            self.fail()
        except Exception as e:
            # expected
            print(str(e))

        try:
            # same team
            team = self.workSchedule.createTeam("Team", "Team", rotation, startRotation)
            self.fail()
        except Exception as e:
            # expected
            print(str(e))

        try:
            # date before start
            team.getDayInRotation(date(2016, 1, 1))
            self.fail()
        except Exception as e:
            # expected
            print(str(e))

        try:
            # end before start
            self.workSchedule.printShiftInstances(date(2017, 1, 2), date(2017, 1, 1))
            self.fail()
        except Exception as e:
            # expected
            print(str(e))

        try:
            # delete in-use shift
            self.workSchedule.deleteShift(shift)
            self.fail()
        except Exception as e:
            # expected
            print(str(e))

        # breaks
        lunch = shift.createBreak("Lunch", "Lunch", time(12, 0, 0), timedelta(minutes=60))
        lunch.setDuration(timedelta(minutes=30))
        lunch.startTime = time(11, 30, 0)
        shift.removeBreak(lunch)
        shift.removeBreak(lunch)

        shift2 = self.workSchedule.createShift("Test2", "Test shift2", shiftStart, shiftDuration)
        self.assertFalse(shift == shift2)

        lunch2 = shift2.createBreak("Lunch2", "Lunch", time(12, 0, 0), timedelta(minutes=60))
        shift.removeBreak(lunch2)
        
        # ok to delete
        schedule2 = WorkSchedule("Exceptions2", "Test exceptions2")
        schedule2.name = "Schedule 2"
        schedule2.description = "a description"

        schedule2.deleteShift(shift)
        schedule2.deleteTeam(team)
        schedule2.deleteNonWorkingPeriod(period)

        # nulls
        try:
            self.workSchedule.createShift("1", "1", None, timedelta(minutes=60))
            self.fail()
        except Exception as e:
            # expected
            print(str(e))

        try:
            self.workSchedule.createShift("1", "1", shiftStart, None)
            self.fail()
        except Exception as e:
            # expected
            print(str(e))

        try:
            self.workSchedule.createShift(None, "1", shiftStart, timedelta(minutes=60))
            self.fail()
        except Exception as e:
            # expected
            print(str(e))

        self.assertFalse(shift == rotation)

        # hashcode()
        team.__hash__()
        teams = {}
        teams[team.name] = team
        value = teams[team.name]
        self.assertTrue(value is not None)
    
    def testShiftWorkingTime(self):
        self.workSchedule = WorkSchedule("Working Time1", "Test working time")

        # shift does not cross midnight
        shiftDuration = timedelta(hours=8)
        shiftStart = time(7, 0, 0)

        shift = self.workSchedule.createShift("Work Shift1", "Working time shift", shiftStart, shiftDuration)
        shiftEnd = shift.getEndTime()

        # case #1
        duration = shift.calculateWorkingTime(time(hour=shiftStart.hour-3), time(hour=shiftStart.hour-2))
        self.assertTrue(duration.total_seconds() == 0)
        workingTime = shift.calculateWorkingTime(time(hour=shiftStart.hour-3), time(hour=shiftStart.hour-3))
        self.assertTrue(workingTime.total_seconds() == 0)
    
        # case #2
        workingTime = shift.calculateWorkingTime(time(shiftStart.hour-1), time(shiftStart.hour+1))
        self.assertTrue(workingTime.total_seconds() == 3600)

        # case #3
        workingTime = shift.calculateWorkingTime(time(shiftStart.hour+1), time(shiftStart.hour+2))
        self.assertTrue(workingTime.total_seconds() == 3600)

        # case #4
        workingTime = shift.calculateWorkingTime(time(shiftEnd.hour-1), time(shiftEnd.hour+1))
        self.assertTrue(workingTime.total_seconds() == 3600)

        # case #5
        workingTime = shift.calculateWorkingTime(time(shiftEnd.hour+1), time(shiftEnd.hour+2))
        self.assertTrue(workingTime.total_seconds() == 0)
        workingTime = shift.calculateWorkingTime(time(shiftEnd.hour+1), time(shiftEnd.hour+1))
        self.assertTrue(workingTime.total_seconds() == 0)

        # case #6
        workingTime = shift.calculateWorkingTime(time(shiftStart.hour-1), time(shiftEnd.hour+1))
        self.assertTrue(workingTime.total_seconds() == shiftDuration.total_seconds())

        # case #7
        workingTime = shift.calculateWorkingTime(time(shiftStart.hour+1), time(shiftStart.hour+1))
        self.assertTrue(workingTime.total_seconds() == 0)

        # case #8
        workingTime = shift.calculateWorkingTime(time(shiftStart.hour), time(shiftEnd.hour))
        self.assertTrue(workingTime.total_seconds() == shiftDuration.total_seconds())

        # case #9
        workingTime = shift.calculateWorkingTime(time(shiftStart.hour), time(shiftStart.hour))
        self.assertTrue(workingTime.total_seconds() == 0)

        # case #10
        workingTime = shift.calculateWorkingTime(shiftEnd, shiftEnd)
        self.assertTrue(workingTime.total_seconds() == 0)

        # case #11
        workingTime = shift.calculateWorkingTime(time(shiftStart.hour), time(shiftStart.hour, shiftStart.minute, shiftStart.second+1))
        self.assertTrue(workingTime.total_seconds() == 1)

        # case #12
        workingTime = shift.calculateWorkingTime(time(shiftEnd.hour-1), shiftEnd)
        self.assertTrue(workingTime.total_seconds() == 3600)

        # 8 hr shift crossing midnight
        shiftStart = time(22, 0, 0)

        shift = self.workSchedule.createShift("Work Shift2", "Working time shift spans midnight", shiftStart, shiftDuration)
        shiftEnd = shift.getEndTime()

        # case #1
        workingTime = shift.calculateTotalWorkingTime(time(shiftStart.hour-3), time(shiftStart.hour-2), True)
        self.assertTrue(workingTime.total_seconds() == 0)
        workingTime = shift.calculateTotalWorkingTime(time(shiftStart.hour-3), time(shiftStart.hour-3), True)
        self.assertTrue(workingTime.total_seconds() == 0)

        # case #2
        workingTime = shift.calculateTotalWorkingTime(time(shiftStart.hour-1), time(shiftStart.hour+1), True)
        self.assertTrue(workingTime.total_seconds() == 3600)

        # case #3
        workingTime = shift.calculateTotalWorkingTime(time(shiftStart.hour+1), time.min, True)
        self.assertTrue(workingTime.total_seconds() == 3600)

        # case #4
        workingTime = shift.calculateTotalWorkingTime(time(shiftEnd.hour-1), time(shiftEnd.hour+1), False)
        self.assertTrue(workingTime.total_seconds() == 3600)

        # case #5
        workingTime = shift.calculateTotalWorkingTime(time(shiftEnd.hour+1), time(shiftEnd.hour+2), True)
        self.assertTrue(workingTime.total_seconds() == 0)
        workingTime = shift.calculateTotalWorkingTime(time(shiftEnd.hour+1), time(shiftEnd.hour+1), True)
        self.assertTrue(workingTime.total_seconds() == 0)

        # case #6
        workingTime = shift.calculateTotalWorkingTime(time(shiftStart.hour-1), time(shiftEnd.hour+1), True)
        self.assertTrue(workingTime.total_seconds() == shiftDuration.total_seconds())

        # case #7
        workingTime = shift.calculateTotalWorkingTime(time(shiftStart.hour+1), time(shiftStart.hour+1), True)
        self.assertTrue(workingTime.total_seconds() == 0)

        # case #8
        workingTime = shift.calculateTotalWorkingTime(shiftStart, shiftEnd, True)
        self.assertTrue(workingTime.total_seconds() == shiftDuration.total_seconds())

        # case #9
        workingTime = shift.calculateTotalWorkingTime(shiftStart, shiftStart, True)
        self.assertTrue(workingTime.total_seconds() == 0)

        # case #10
        workingTime = shift.calculateTotalWorkingTime(shiftEnd, shiftEnd, True)
        self.assertTrue(workingTime.total_seconds() == 0)

        # case #11
        workingTime = shift.calculateTotalWorkingTime(shiftStart, time(shiftStart.hour, shiftStart.minute, shiftStart.second+1), True)
        self.assertTrue(workingTime.total_seconds() == 1)

        # case #12
        workingTime = shift.calculateTotalWorkingTime(time(shiftEnd.hour-1), shiftEnd, False)
        self.assertTrue(workingTime.total_seconds() == 3600)

        # 24 hr shift crossing midnight
        shiftDuration = timedelta(hours=24)
        shiftStart = time(7, 0, 0)

        shift = self.workSchedule.createShift("Work Shift3", "Working time shift", shiftStart, shiftDuration)
        shiftEnd = shift.getEndTime()

        # case #1
        workingTime = shift.calculateTotalWorkingTime(time(shiftStart.hour-3), time(shiftStart.hour-2), False)
        self.assertTrue(workingTime.total_seconds() == 3600)
        workingTime = shift.calculateTotalWorkingTime(time(shiftStart.hour-3), time(shiftStart.hour-3), True)
        self.assertTrue(workingTime.total_seconds() == 0)

        # case #2
        workingTime = shift.calculateTotalWorkingTime(time(shiftStart.hour-1), time(shiftStart.hour+1), True)
        self.assertTrue(workingTime.total_seconds() == 3600)

        # case #3
        workingTime = shift.calculateTotalWorkingTime(time(shiftStart.hour+1), time(shiftStart.hour+2), True)
        self.assertTrue(workingTime.total_seconds() == 3600)

        # case #4
        workingTime = shift.calculateTotalWorkingTime(time(shiftEnd.hour-1), time(shiftEnd.hour+1), True)
        self.assertTrue(workingTime.total_seconds() == 3600)

        # case #5
        workingTime = shift.calculateTotalWorkingTime(time(shiftEnd.hour+1), time(shiftEnd.hour+2), True)
        self.assertTrue(workingTime.total_seconds() == 3600)
        workingTime = shift.calculateTotalWorkingTime(time(shiftEnd.hour+1), time(shiftEnd.hour+1), True)
        self.assertTrue(workingTime.total_seconds() == 0)

        # case #6
        workingTime = shift.calculateTotalWorkingTime(time(shiftStart.hour-1), time(shiftEnd.hour+1), True)
        self.assertTrue(workingTime.total_seconds() == 3600)

        # case #7
        workingTime = shift.calculateTotalWorkingTime(time(shiftStart.hour+1), time(shiftStart.hour+1), True)
        self.assertTrue(workingTime.total_seconds() == 0)

        # case #8
        workingTime = shift.calculateTotalWorkingTime(shiftStart, shiftEnd, True)
        self.assertTrue(workingTime.total_seconds() == shiftDuration.total_seconds())

        # case #9
        workingTime = shift.calculateTotalWorkingTime(shiftStart, shiftStart, True)
        self.assertTrue(workingTime.total_seconds() == shiftDuration.total_seconds())

        # case #10
        workingTime = shift.calculateTotalWorkingTime(shiftEnd, shiftEnd, True)
        self.assertTrue(workingTime.total_seconds() == shiftDuration.total_seconds())

        # case #11
        workingTime = shift.calculateTotalWorkingTime(shiftStart, time(shiftStart.hour, shiftStart.minute, shiftStart.second+1), True)
        self.assertTrue(workingTime.total_seconds() == 1)

        # case #12
        workingTime = shift.calculateTotalWorkingTime(time(shiftEnd.hour-1), shiftEnd, False)
        self.assertTrue(workingTime.total_seconds() == 3600)
        
    
    def testTeamWorkingTime(self):
        self.workSchedule = WorkSchedule("Team Working Time", "Test team working time")
        shiftDuration = timedelta(hours=12)
        halfShift = timedelta(hours=6)
        shiftStart = time(7, 0, 0)

        shift = self.workSchedule.createShift("Team Shift1", "Team shift 1", shiftStart, shiftDuration)

        rotation = self.workSchedule.createRotation("Team", "Rotation")
        rotation.addSegment(shift, 1, 1)

        startRotation = date(2017, 1, 1)
        team = self.workSchedule.createTeam("Team", "Team", rotation, startRotation)
        team.rotationStart = startRotation

        # case #1
        fromDateTime = datetime.combine(startRotation, shiftStart) + timedelta(days=rotation.getDayCount())
        toDateTime = fromDateTime + timedelta(days=1)
        workingTime = team.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(workingTime == shiftDuration)

        # case #2
        toDateTime = fromDateTime + timedelta(days=2)
        workingTime = team.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(workingTime == shiftDuration)

        # case #3
        toDateTime = fromDateTime + timedelta(days=3)
        workingTime = team.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(workingTime == shiftDuration + shiftDuration)

        # case #4
        toDateTime = fromDateTime + timedelta(days=4)
        workingTime = team.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(workingTime == shiftDuration + shiftDuration)

        # case #5
        fromDateTime = datetime.combine(startRotation, shiftStart) + timedelta(days=rotation.getDayCount(), hours=6)
        toDateTime = fromDateTime + timedelta(days=1)
        workingTime = team.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(workingTime == halfShift)

        # case #6
        toDateTime = fromDateTime + timedelta(days=2)
        workingTime = team.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(workingTime == shiftDuration)

        # case #7
        toDateTime = fromDateTime + timedelta(days=3)
        workingTime = team.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(workingTime == shiftDuration + halfShift)

        # case #8
        toDateTime = fromDateTime + timedelta(days=4)
        workingTime = team.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(workingTime == shiftDuration + shiftDuration)

        # now crossing midnight
        shiftStart = time(18, 0, 0)
        shift2 = self.workSchedule.createShift("Team Shift2", "Team shift 2", shiftStart, shiftDuration)

        rotation2 = self.workSchedule.createRotation("Case 8", "Case 8")
        rotation2.addSegment(shift2, 1, 1)

        team2 = self.workSchedule.createTeam("Team2", "Team 2", rotation2, startRotation)
        team2.rotationStart = startRotation

        # case #1
        fromDateTime = datetime.combine(startRotation, shiftStart) + timedelta(days=rotation.getDayCount())
        toDateTime = fromDateTime + timedelta(days=1)
        workingTime = team2.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(workingTime == shiftDuration)

        # case #2
        toDateTime = fromDateTime + timedelta(days=2)
        workingTime = team2.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(workingTime == shiftDuration)

        # case #3
        toDateTime = fromDateTime + timedelta(days=3)
        workingTime = team2.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(workingTime == shiftDuration + shiftDuration)

        # case #4
        toDateTime = fromDateTime + timedelta(days=4)
        workingTime = team2.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(workingTime == shiftDuration + shiftDuration)

        # case #5
        dayDelta = datetime.combine(startRotation, shiftStart) + timedelta(days=rotation.getDayCount())
        fromDateTime = datetime.combine(dayDelta.date(), time.max)
        toDateTime = fromDateTime + timedelta(days=1)
        workingTime = team2.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(workingTime == halfShift)

        # case #6
        toDateTime = fromDateTime + timedelta(days=2)
        workingTime = team2.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(workingTime == shiftDuration)

        # case #7
        toDateTime = fromDateTime + timedelta(days=3)
        workingTime = team2.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(workingTime == shiftDuration + halfShift)

        # case #8
        toDateTime = fromDateTime + timedelta(days=4)
        workingTime = team2.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(workingTime == shiftDuration + shiftDuration)
    
    
    def testNonWorkingTime(self): 
        self.workSchedule =  WorkSchedule("Non Working Time", "Test non working time")
        localDate = date(2017, 1, 1)
        localTime = time(7, 0, 0)

        period1 = self.workSchedule.createNonWorkingPeriod("Day1", "First test day",
                datetime.combine(localDate, time.min), timedelta(hours=24))
        print(period1.__str__())
        
        period2 = self.workSchedule.createNonWorkingPeriod("Day2", "First test day",
                datetime.combine(localDate, localTime) + timedelta(days=7), timedelta(hours=24))
        print(period1.__str__())

        fromDateTime = datetime.combine(localDate, localTime)
        toDateTime = datetime.combine(localDate, time(localTime.hour+1))

        # case #1
        duration = self.workSchedule.calculateNonWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=1))

        # case #2
        fromDateTime = datetime.combine(localDate, localTime) - timedelta(days=1)
        toDateTime = datetime.combine(localDate, localTime) + timedelta(days=1)
        duration = self.workSchedule.calculateNonWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=24))

        # case #3
        fromDateTime = datetime.combine(localDate, localTime) - timedelta(days=1)
        toDateTime = datetime.combine(localDate, time(localTime.hour+1)) - timedelta(days=1)
        duration = self.workSchedule.calculateNonWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=0))

        # case #4
        fromDateTime = datetime.combine(localDate, localTime) + timedelta(days=1)
        toDateTime = datetime.combine(localDate, time(localTime.hour+1)) + timedelta(days=1)
        duration = self.workSchedule.calculateNonWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=0))

        # case #5
        fromDateTime = datetime.combine(localDate, localTime) - timedelta(days=1)
        toDateTime = datetime.combine(localDate, localTime)
        duration = self.workSchedule.calculateNonWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=7))

        # case #6
        fromDateTime = datetime.combine(localDate, localTime)
        toDateTime = datetime.combine(localDate, localTime) + timedelta(days=1)
        duration = self.workSchedule.calculateNonWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=17))

        # case #7
        fromDateTime = datetime.combine(localDate, time(hour=12))
        toDateTime = datetime.combine(localDate, time(hour=12)) + timedelta(days=7)
        duration = self.workSchedule.calculateNonWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=17))

        # case #8
        fromDateTime = datetime.combine(localDate, time(hour=12)) - timedelta(days=1)
        toDateTime = datetime.combine(localDate, time(hour=12)) + timedelta(days=8)
        duration = self.workSchedule.calculateNonWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=48))

        # case #9
        self.workSchedule.deleteNonWorkingPeriod(period1)
        self.workSchedule.deleteNonWorkingPeriod(period2)
        fromDateTime = datetime.combine(localDate, localTime)
        toDateTime = datetime.combine(localDate, time(localTime.hour+1))

        # case #10
        duration = self.workSchedule.calculateNonWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=0))

        shiftDuration = timedelta(hours=8)
        shiftStart = time(7, 0, 0)

        shift = self.workSchedule.createShift("Work Shift1", "Working time shift", shiftStart, shiftDuration)

        rotation = self.workSchedule.createRotation("Case 10", "Case10")
        rotation.addSegment(shift, 1, 1)

        startRotation = date(2017, 1, 1)
        team = self.workSchedule.createTeam("Team", "Team", rotation, startRotation)
        team.rotationStart = startRotation

        period1 = self.workSchedule.createNonWorkingPeriod("Day1", "First test day", datetime.combine(localDate, time.min),
            timedelta(hours=24))

        mark = localDate + timedelta(days=rotation.getDayCount())
        fromDateTime = datetime.combine(mark, time(hour=localTime.hour-2))
        toDateTime = datetime.combine(mark, time(hour=localTime.hour-1))

        # case #11
        duration = self.workSchedule.calculateWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=0))

        # case #12
        fromDateTime = datetime.combine(localDate, shiftStart)
        toDateTime = datetime.combine(localDate, time(localTime.hour+8))

        duration = self.workSchedule.calculateNonWorkingTime(fromDateTime, toDateTime)
        self.assertTrue(duration == timedelta(hours=8))
    
    def testTeamMembers(self):
        self.workSchedule = WorkSchedule("Restaurant", "Two shifts")

        # day shift (12 hours)
        day = self.workSchedule.createShift("Day", "Green", time(6, 0, 0), timedelta(hours=12))

        # night shift (3 hours)
        night = self.workSchedule.createShift("Night", "Blue", time(18, 0, 0), timedelta(hours=3))

        # day shift rotation, 1 days ON, 0 OFF
        dayRotation = self.workSchedule.createRotation("Day", "One day on, 6 off")
        dayRotation.addSegment(day, 1, 6)

        nightRotation = self.workSchedule.createRotation("Night", "One day on, 6 off")
        nightRotation.addSegment(night, 1, 6)

        # day teams
        greenStart = date(2024, 7, 28)
        sundayDay = self.workSchedule.createTeam("SundayDay", "Sunday day", dayRotation, greenStart)
        mondayDay = self.workSchedule.createTeam("MondayDay", "Monday day", dayRotation, greenStart + timedelta(days=1))
        tuesdayDay = self.workSchedule.createTeam("TuesdayDay", "Tuesday day", dayRotation, greenStart + timedelta(days=2))
        wednesdayDay = self.workSchedule.createTeam("WednesdayDay", "Wednesday day", dayRotation, greenStart + timedelta(days=3))
        thursdayDay = self.workSchedule.createTeam("ThursdayDay", "Thursday day", dayRotation, greenStart + timedelta(days=4))
        fridayDay = self.workSchedule.createTeam("FridayDay", "Friday day", dayRotation, greenStart + timedelta(days=5))
        saturdayDay = self.workSchedule.createTeam("SaturdayDay", "Saturday day", dayRotation, greenStart + timedelta(days=6))

        # night teams
        blueStart = date(2024, 7, 29)
        mondayNight = self.workSchedule.createTeam("MondayNight", "Monday night", nightRotation, blueStart)
        tuesdayNight = self.workSchedule.createTeam("TuesdayNight", "Tuesday night", nightRotation, blueStart + timedelta(days=1))
        wednesdayNight = self.workSchedule.createTeam("WednesdayNight", "Wednesday night", nightRotation,
                blueStart + timedelta(days=2))
        thursdayNight = self.workSchedule.createTeam("ThursdayNight", "Thursday night", nightRotation,
                blueStart + timedelta(days=3))
        fridayNight = self.workSchedule.createTeam("FridayNight", "Friday night", nightRotation, blueStart + timedelta(days=4))
        saturdayNight = self.workSchedule.createTeam("SaturdayNight", "Saturday night", nightRotation,
                blueStart + timedelta(days=5))

        # chef members
        one = TeamMember("Chef, One", "Chef", "1")
        two = TeamMember("Chef, Two", "Chef", "2")
        three = TeamMember("Chef, Three", "Chef", "3")
        four = TeamMember("Chef, Four", "Chef", "4")
        five = TeamMember("Chef, Five", "Chef", "5")
        six = TeamMember("Chef, Six", "Chef", "6")
        seven = TeamMember("Chef, Seven", "Chef", "7")

        # helper members
        eight = TeamMember("Helper, One", "Helper", "8")
        nine = TeamMember("Helper, Two", "Helper", "9")

        # day members
        sundayDay.addMember(one)
        sundayDay.addMember(two)
        sundayDay.addMember(eight)
        mondayDay.addMember(one)
        mondayDay.addMember(two)
        mondayDay.addMember(nine)
        tuesdayDay.addMember(three)
        wednesdayDay.addMember(four)
        thursdayDay.addMember(five)
        fridayDay.addMember(six)
        saturdayDay.addMember(seven)

        # night members
        mondayNight.addMember(four)
        tuesdayNight.addMember(five)
        wednesdayNight.addMember(six)
        thursdayNight.addMember(seven)
        fridayNight.addMember(one)
        saturdayNight.addMember(two)

        self.workSchedule.printShiftInstances(date(2024, 8, 4), date(2024, 8, 11))

        for team in self.workSchedule.teams:
            print(team.__str__())

        self.assertTrue(sundayDay.hasMember(two))

        sundayDay.removeMember(two)

        self.assertFalse(sundayDay.hasMember(two))

        # member exceptions
        ten = TeamMember("Ten", "Ten description", "10")

        # replace one with ten
        exceptionShift = datetime.combine(date(2024, 8, 11), time(7, 0, 0))
        replacement = TeamMemberException(exceptionShift)
        replacement.removal = one
        replacement.addition = ten
        sundayDay.addMemberException(replacement)

        self.assertTrue(one in sundayDay.assignedMembers)
        self.assertFalse(ten in sundayDay.assignedMembers)

        members = sundayDay.getMembers(exceptionShift)
        
        for member in members:
            print(str(member))

        self.assertFalse(one in members)
        self.assertTrue(ten in members)

        for team in self.workSchedule.teams:
            print(str(team))    