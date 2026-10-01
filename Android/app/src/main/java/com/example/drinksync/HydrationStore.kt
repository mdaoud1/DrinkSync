package com.example.drinksync

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import java.time.LocalDate
import java.time.LocalTime
import java.time.temporal.ChronoUnit

object HydrationKeys {
    const val CURRENT_INTAKE = "currentIntake"
    const val TOTAL_INTAKE = "totalIntake"
    const val DAILY_GOAL = "dailyGoal"
    const val HAS_HIT_GOAL = "hasHitGoal"
    const val STREAK = "streak"
    const val LAST_RESET_DATE = "lastResetDate"
    const val NOTIFICATIONS = "notifications"
    const val FIRST_SIP = "firstSip"
    const val HALFWAY_TO_GOAL = "halfwayToGoal"
    const val HYDRATION_HERO = "hydrationHero"
    const val BIG_GULP = "bigGulp"
    const val LATE_NIGHT_SIP = "lateNightSip"
    const val EARLY_BIRD = "earlyBirdDrinker"
    const val NOTIFICATION_TRIGGERS = "notificationTriggers"
    const val LEFTOVER_GRAMS = "leftoverGrams"
}

data class HydrationSnapshot(
    val currentIntake: Int,
    val totalIntake: Int,
    val dailyGoal: Int,
    val hasHitGoal: Boolean,
    val streak: Int,
    val lastResetDate: String,
    val notifications: Boolean,
    val firstSip: Boolean,
    val halfwayToGoal: Boolean,
    val hydrationHero: Boolean,
    val bigGulp: Boolean,
    val lateNightSip: Boolean,
    val earlyBirdDrinker: Boolean,
    val notificationTriggers: Set<Int>,
    val leftoverGrams: Double,
)

class HydrationStore(
    val prefs: PrefsLike,
    private val today: () -> LocalDate = { LocalDate.now() },
    private val nowTime: () -> LocalTime = { LocalTime.now() },
) {
    var snapshot by mutableStateOf(load())
        private set

    fun addIntake(amountOz: Int) {
        if (amountOz <= 0) return
        applyDailyResetIfNeeded()
        applyIntake(
            newCurrent = snapshot.currentIntake + amountOz,
            newTotal = snapshot.totalIntake + amountOz,
            loggedAmount = amountOz,
        )
    }

    fun addGrams(grams: Double) {
        if (grams <= 0) return
        applyDailyResetIfNeeded()
        val (ounces, leftover) = DrinkEvent.leftoverAfterAdding(snapshot.leftoverGrams, grams)
        persistLeftover(leftover)
        snapshot = snapshot.copy(leftoverGrams = leftover)
        if (ounces > 0) {
            addIntake(ounces)
        }
    }

    fun setIntake(newIntake: Int) {
        if (newIntake < 0) return
        applyDailyResetIfNeeded()
        val delta = newIntake - snapshot.currentIntake
        applyIntake(
            newCurrent = newIntake,
            newTotal = (snapshot.totalIntake + delta).coerceAtLeast(0),
            loggedAmount = 0,
        )
    }

    fun setDailyGoal(goal: Int) {
        if (goal !in 1..500) return
        prefs.saveInt(HydrationKeys.DAILY_GOAL, goal)
        snapshot = snapshot.copy(dailyGoal = goal).withGoalFlags()
        persistGoalFlags(snapshot)
    }

    fun setNotifications(enabled: Boolean) {
        prefs.saveBoolean(HydrationKeys.NOTIFICATIONS, enabled)
        snapshot = snapshot.copy(notifications = enabled)
    }

    fun markNotificationTrigger(percent: Int) {
        val triggers = snapshot.notificationTriggers + percent
        prefs.saveStringSet(HydrationKeys.NOTIFICATION_TRIGGERS, triggers.map { it.toString() }.toSet())
        snapshot = snapshot.copy(notificationTriggers = triggers)
    }

    fun applyDailyResetIfNeeded() {
        val todayDate = today()
        val stored = prefs.getString(HydrationKeys.LAST_RESET_DATE, null)
        if (stored.isNullOrBlank()) {
            prefs.saveString(HydrationKeys.LAST_RESET_DATE, todayDate.toString())
            snapshot = snapshot.copy(lastResetDate = todayDate.toString())
            return
        }
        val last = runCatching { LocalDate.parse(stored) }.getOrNull()
        if (last == null) {
            prefs.saveString(HydrationKeys.LAST_RESET_DATE, todayDate.toString())
            snapshot = snapshot.copy(lastResetDate = todayDate.toString())
            return
        }
        if (last == todayDate) return

        val daysMissed = ChronoUnit.DAYS.between(last, todayDate)
        val newStreak = if (daysMissed == 1L && snapshot.hasHitGoal) snapshot.streak + 1 else 0
        val reset = snapshot.copy(
            currentIntake = 0,
            hasHitGoal = false,
            halfwayToGoal = false,
            streak = newStreak,
            lastResetDate = todayDate.toString(),
            notificationTriggers = emptySet(),
        )
        prefs.saveInt(HydrationKeys.CURRENT_INTAKE, 0)
        prefs.saveBoolean(HydrationKeys.HAS_HIT_GOAL, false)
        prefs.saveBoolean(HydrationKeys.HALFWAY_TO_GOAL, false)
        prefs.saveInt(HydrationKeys.STREAK, newStreak)
        prefs.saveString(HydrationKeys.LAST_RESET_DATE, todayDate.toString())
        prefs.saveStringSet(HydrationKeys.NOTIFICATION_TRIGGERS, emptySet())
        snapshot = reset
    }

    private fun applyIntake(newCurrent: Int, newTotal: Int, loggedAmount: Int) {
        var next = snapshot.copy(currentIntake = newCurrent, totalIntake = newTotal)
        if (newCurrent > 0) {
            next = next.copy(firstSip = true)
        }
        next = next.withGoalFlags()
        if (loggedAmount > 0) {
            val hour = nowTime().hour
            if (hour in 0..2) next = next.copy(lateNightSip = true)
            if (hour in 5..6) next = next.copy(earlyBirdDrinker = true)
            if (loggedAmount >= 32) next = next.copy(bigGulp = true)
        }
        prefs.saveInt(HydrationKeys.CURRENT_INTAKE, next.currentIntake)
        prefs.saveInt(HydrationKeys.TOTAL_INTAKE, next.totalIntake)
        persistGoalFlags(next)
        prefs.saveBoolean(HydrationKeys.FIRST_SIP, next.firstSip)
        prefs.saveBoolean(HydrationKeys.HYDRATION_HERO, next.hydrationHero)
        prefs.saveBoolean(HydrationKeys.BIG_GULP, next.bigGulp)
        prefs.saveBoolean(HydrationKeys.LATE_NIGHT_SIP, next.lateNightSip)
        prefs.saveBoolean(HydrationKeys.EARLY_BIRD, next.earlyBirdDrinker)
        snapshot = next
    }

    private fun HydrationSnapshot.withGoalFlags(): HydrationSnapshot {
        val goal = dailyGoal
        val halfway = if (goal > 0) currentIntake * 2 >= goal else false
        val hit = if (goal > 0) currentIntake >= goal else false
        return copy(
            halfwayToGoal = halfway,
            hasHitGoal = hit,
            hydrationHero = hydrationHero || hit,
        )
    }

    private fun persistLeftover(grams: Double) {
        prefs.saveString(HydrationKeys.LEFTOVER_GRAMS, grams.toString())
    }

    private fun persistGoalFlags(state: HydrationSnapshot) {
        prefs.saveBoolean(HydrationKeys.HAS_HIT_GOAL, state.hasHitGoal)
        prefs.saveBoolean(HydrationKeys.HALFWAY_TO_GOAL, state.halfwayToGoal)
        prefs.saveBoolean(HydrationKeys.HYDRATION_HERO, state.hydrationHero)
    }

    private fun load(): HydrationSnapshot {
        val todayDate = today().toString()
        return HydrationSnapshot(
            currentIntake = prefs.getInt(HydrationKeys.CURRENT_INTAKE, 0),
            totalIntake = prefs.getInt(HydrationKeys.TOTAL_INTAKE, 0),
            dailyGoal = prefs.getInt(HydrationKeys.DAILY_GOAL, 64),
            hasHitGoal = prefs.getBoolean(HydrationKeys.HAS_HIT_GOAL, false),
            streak = prefs.getInt(HydrationKeys.STREAK, 0),
            lastResetDate = prefs.getString(HydrationKeys.LAST_RESET_DATE, null) ?: todayDate,
            notifications = prefs.getBoolean(HydrationKeys.NOTIFICATIONS, true),
            firstSip = prefs.getBoolean(HydrationKeys.FIRST_SIP, false),
            halfwayToGoal = prefs.getBoolean(HydrationKeys.HALFWAY_TO_GOAL, false),
            hydrationHero = prefs.getBoolean(HydrationKeys.HYDRATION_HERO, false),
            bigGulp = prefs.getBoolean(HydrationKeys.BIG_GULP, false),
            lateNightSip = prefs.getBoolean(HydrationKeys.LATE_NIGHT_SIP, false),
            earlyBirdDrinker = prefs.getBoolean(HydrationKeys.EARLY_BIRD, false),
            notificationTriggers = prefs.getStringSet(HydrationKeys.NOTIFICATION_TRIGGERS, emptySet())
                ?.mapNotNull { it.toIntOrNull() }
                ?.toSet()
                ?: emptySet(),
            leftoverGrams = prefs.getString(HydrationKeys.LEFTOVER_GRAMS, null)?.toDoubleOrNull() ?: 0.0,
        )
    }
}
