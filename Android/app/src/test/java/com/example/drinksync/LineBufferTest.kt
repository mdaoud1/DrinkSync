package com.example.drinksync

import org.junit.Assert.assertEquals
import org.junit.Test

class LineBufferTest {
    @Test
    fun splitsCompleteLines() {
        val buffer = LineBuffer()
        assertEquals(
            listOf("Weight difference: 12.50 grams"),
            buffer.add("Weight difference: 12.50 grams\n"),
        )
    }

    @Test
    fun holdsPartialLineUntilNewline() {
        val buffer = LineBuffer()
        assertEquals(emptyList<String>(), buffer.add("Weight difference: "))
        assertEquals(
            listOf("Weight difference: 8.00 grams"),
            buffer.add("8.00 grams\n"),
        )
    }

    @Test
    fun acceptsLegacyMessageWithoutNewline() {
        val buffer = LineBuffer()
        assertEquals(
            listOf("Weight difference: 12.50 grams"),
            buffer.add("Weight difference: 12.50 grams"),
        )
    }

    @Test
    fun splitsTwoMessagesInOneChunk() {
        val buffer = LineBuffer()
        assertEquals(
            listOf(
                "Weight difference: 12.50 grams",
                "Weight difference: 8.00 grams",
            ),
            buffer.add("Weight difference: 12.50 grams\nWeight difference: 8.00 grams\n"),
        )
    }
}
