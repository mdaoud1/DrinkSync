package com.example.drinksync

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDate

class HydrationStoreTest {
    private fun store(
        today: LocalDate = LocalDate.of(2026, 8, 15),
        lastReset: LocalDate = today,
        currentIntake: Int = 0,
        totalIntake: Int = 0,
        dailyGoal: Int = 64,
        hasHitGoal: Boolean = false,
        streak: Int = 0,
    ): HydrationStore {
        val memory = MemoryPrefs()
        memory.saveInt(HydrationKeys.CURRENT_INTAKE, currentIntake)
        memory.saveInt(HydrationKeys.TOTAL_INTAKE, totalIntake)
        memory.saveInt(HydrationKeys.DAILY_GOAL, dailyGoal)
        memory.saveBoolean(HydrationKeys.HAS_HIT_GOAL, hasHitGoal)
        memory.saveInt(HydrationKeys.STREAK, streak)
        memory.saveString(HydrationKeys.LAST_RESET_DATE, lastReset.toString())
        return HydrationStore(memory, today = { today })
    }

    @Test
    fun setIntakePersistsCurrentAndAdjustsTotal() {
        val store = store(currentIntake = 8, totalIntake = 20)
        store.setIntake(20)
        assertEquals(20, store.snapshot.currentIntake)
        assertEquals(32, store.snapshot.totalIntake)
        assertEquals(20, store.prefs.getInt(HydrationKeys.CURRENT_INTAKE, -1))
        assertEquals(32, store.prefs.getInt(HydrationKeys.TOTAL_INTAKE, -1))
    }

    @Test
    fun addIntakePersistsRunningTotal() {
        val store = store()
        store.addIntake(8)
        assertEquals(8, store.snapshot.currentIntake)
        assertEquals(8, store.prefs.getInt(HydrationKeys.CURRENT_INTAKE, -1))
    }

    @Test
    fun setDailyGoalIsReadableOnNextSnapshot() {
        val store = store(dailyGoal = 64)
        store.setDailyGoal(80)
        assertEquals(80, store.snapshot.dailyGoal)
    }

    @Test
    fun nextDayAfterHitIncrementsStreakAndZerosIntake() {
        val today = LocalDate.of(2026, 8, 16)
        val store = store(
            today = today,
            lastReset = LocalDate.of(2026, 8, 15),
            currentIntake = 70,
            hasHitGoal = true,
            streak = 2,
        )
        store.applyDailyResetIfNeeded()
        assertEquals(0, store.snapshot.currentIntake)
        assertEquals(3, store.snapshot.streak)
        assertFalse(store.snapshot.hasHitGoal)
        assertEquals(today.toString(), store.snapshot.lastResetDate)
    }

    @Test
    fun skippedDaysBreakStreakEvenIfLastOpenDayHitGoal() {
        val today = LocalDate.of(2026, 8, 18)
        val store = store(
            today = today,
            lastReset = LocalDate.of(2026, 8, 15),
            hasHitGoal = true,
            streak = 4,
            currentIntake = 40,
        )
        store.applyDailyResetIfNeeded()
        assertEquals(0, store.snapshot.streak)
        assertEquals(0, store.snapshot.currentIntake)
        assertEquals(today.toString(), store.snapshot.lastResetDate)
    }

    @Test
    fun sameDayDoesNotReset() {
        val store = store(currentIntake = 12, streak = 1)
        store.applyDailyResetIfNeeded()
        assertEquals(12, store.snapshot.currentIntake)
        assertEquals(1, store.snapshot.streak)
    }

    @Test
    fun firstSipUnlocksWhenIntakeBecomesPositive() {
        val store = store()
        assertFalse(store.snapshot.firstSip)
        store.addIntake(8)
        assertTrue(store.snapshot.firstSip)
    }

    @Test
    fun missingLastResetDateIsWrittenSoTheNextDayResets() {
        val memory = MemoryPrefs()
        memory.saveInt(HydrationKeys.CURRENT_INTAKE, 12)
        val day1 = LocalDate.of(2026, 8, 15)
        val firstOpen = HydrationStore(memory, today = { day1 })
        firstOpen.applyDailyResetIfNeeded()
        assertEquals(12, firstOpen.snapshot.currentIntake)
        assertEquals(day1.toString(), memory.getString(HydrationKeys.LAST_RESET_DATE, null))

        val day2 = LocalDate.of(2026, 8, 16)
        val nextOpen = HydrationStore(memory, today = { day2 })
        nextOpen.applyDailyResetIfNeeded()
        assertEquals(0, nextOpen.snapshot.currentIntake)
        assertEquals(day2.toString(), nextOpen.snapshot.lastResetDate)
    }

    @Test
    fun addGramsKeepsRemainderUntilAFullOunce() {
        val store = store()
        store.addGrams(10.0)
        assertEquals(0, store.snapshot.currentIntake)
        store.addGrams(20.0)
        assertEquals(1, store.snapshot.currentIntake)
    }

    @Test
    fun setDailyGoalRejectsZeroAndHugeValues() {
        val store = store(dailyGoal = 64)
        store.setDailyGoal(0)
        assertEquals(64, store.snapshot.dailyGoal)
        store.setDailyGoal(501)
        assertEquals(64, store.snapshot.dailyGoal)
        store.setDailyGoal(80)
        assertEquals(80, store.snapshot.dailyGoal)
    }

    @Test
    fun setIntakeDoesNotLetLifetimeTotalGoNegative() {
        val store = store(currentIntake = 20, totalIntake = 8)
        store.setIntake(0)
        assertEquals(0, store.snapshot.currentIntake)
        assertEquals(0, store.snapshot.totalIntake)
    }

    @Test
    fun addIntakeOnANewDayResetsYesterdayFirst() {
        val memory = MemoryPrefs()
        memory.saveInt(HydrationKeys.CURRENT_INTAKE, 40)
        memory.saveInt(HydrationKeys.TOTAL_INTAKE, 40)
        memory.saveBoolean(HydrationKeys.HAS_HIT_GOAL, false)
        memory.saveString(HydrationKeys.LAST_RESET_DATE, "2026-08-15")
        val store = HydrationStore(memory, today = { LocalDate.of(2026, 8, 16) })
        store.addIntake(8)
        assertEquals(8, store.snapshot.currentIntake)
        assertEquals(48, store.snapshot.totalIntake)
    }

    @Test
    fun halfwayDoesNotUnlockAtZeroWhenGoalIsOne() {
        val store = store(dailyGoal = 64)
        store.setDailyGoal(1)
        assertFalse(store.snapshot.halfwayToGoal)
        store.addIntake(1)
        assertTrue(store.snapshot.halfwayToGoal)
        assertTrue(store.snapshot.hasHitGoal)
    }
}
