package com.example.drinksync

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class DrinkEventTest {
    @Test
    fun parseCanonicalWeightDifference() {
        assertEquals(12.5, DrinkEvent.parseGrams("Weight difference: 12.50 grams")!!, 0.0001)
    }

    @Test
    fun parseAverageWeightAlias() {
        assertEquals(29.57, DrinkEvent.parseGrams("Average weight: 29.57 grams")!!, 0.0001)
    }

    @Test
    fun parseLegacyTypoAlias() {
        assertEquals(8.0, DrinkEvent.parseGrams("Weight Differnce: 8.00 grams")!!, 0.0001)
    }

    @Test
    fun parseAllowsExtraWhitespace() {
        assertEquals(4.0, DrinkEvent.parseGrams("  Weight difference:   4 grams\n")!!, 0.0001)
    }

    @Test
    fun parseRejectsJunk() {
        assertNull(DrinkEvent.parseGrams("hello"))
        assertNull(DrinkEvent.parseGrams(""))
        assertNull(DrinkEvent.parseGrams("Weight difference: abc grams"))
    }

    @Test
    fun parseRejectsNonPositiveGrams() {
        assertNull(DrinkEvent.parseGrams("Weight difference: 0 grams"))
        assertNull(DrinkEvent.parseGrams("Weight difference: -3.2 grams"))
    }

    @Test
    fun gramsToOzRoundsNearest() {
        assertEquals(1, DrinkEvent.gramsToOz(29.5735))
        assertEquals(4, DrinkEvent.gramsToOz(123.4))
        assertEquals(0, DrinkEvent.gramsToOz(10.0))
    }

    @Test
    fun leftoverAfterAddingKeepsSmallSips() {
        val first = DrinkEvent.leftoverAfterAdding(0.0, 10.0)
        assertEquals(0, first.first)
        assertEquals(10.0, first.second, 0.0001)

        val second = DrinkEvent.leftoverAfterAdding(first.second, 20.0)
        assertEquals(1, second.first)
        assertEquals(30.0 - DrinkEvent.GRAMS_PER_OZ, second.second, 0.0001)
    }
}
