package com.example.drinksync

class LineBuffer {
    private val pending = StringBuilder()

    fun add(chunk: String): List<String> {
        pending.append(chunk)
        val lines = mutableListOf<String>()
        while (true) {
            val text = pending.toString()
            val newline = text.indexOf('\n')
            if (newline < 0) break
            val line = text.substring(0, newline).trim()
            pending.delete(0, newline + 1)
            if (line.isNotEmpty()) {
                lines.add(line)
            }
        }
        val remainder = pending.toString().trim()
        if (remainder.isNotEmpty() && DrinkEvent.parseGrams(remainder) != null) {
            lines.add(remainder)
            pending.clear()
        }
        return lines
    }
}
