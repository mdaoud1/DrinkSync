package com.example.drinksync

import kotlin.math.roundToInt

object DrinkEvent {
    const val GRAMS_PER_OZ = 29.5735

    private val message = Regex(
        """^(?:Weight difference|Average weight|Weight Differnce):\s*(-?\d+(?:\.\d+)?)\s*grams$""",
        RegexOption.IGNORE_CASE,
    )

    fun parseGrams(raw: String): Double? {
        val match = message.matchEntire(raw.trim()) ?: return null
        val grams = match.groupValues[1].toDoubleOrNull() ?: return null
        return if (grams > 0) grams else null
    }

    fun gramsToOz(grams: Double): Int = (grams / GRAMS_PER_OZ).roundToInt()

    fun leftoverAfterAdding(existingLeftoverGrams: Double, addedGrams: Double): Pair<Int, Double> {
        val total = existingLeftoverGrams + addedGrams
        val ounces = gramsToOz(total)
        if (ounces <= 0) return 0 to total
        return ounces to (total - ounces * GRAMS_PER_OZ)
    }
}
