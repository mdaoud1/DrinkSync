package com.example.drinksync

interface PrefsLike {
    fun saveInt(key: String, value: Int)
    fun saveBoolean(key: String, value: Boolean)
    fun saveLong(key: String, value: Long)
    fun saveStringSet(key: String, value: Set<String>?)
    fun saveString(key: String, value: String?)
    fun getInt(key: String, defaultValue: Int): Int
    fun getBoolean(key: String, defaultValue: Boolean): Boolean
    fun getLong(key: String, defaultValue: Long): Long
    fun getStringSet(key: String, defaultValue: Set<String>?): Set<String>?
    fun getString(key: String, defaultValue: String?): String?
}

class MemoryPrefs : PrefsLike {
    private val ints = mutableMapOf<String, Int>()
    private val bools = mutableMapOf<String, Boolean>()
    private val longs = mutableMapOf<String, Long>()
    private val strings = mutableMapOf<String, String?>()
    private val stringSets = mutableMapOf<String, Set<String>?>()

    override fun saveInt(key: String, value: Int) {
        ints[key] = value
    }

    override fun saveBoolean(key: String, value: Boolean) {
        bools[key] = value
    }

    override fun saveLong(key: String, value: Long) {
        longs[key] = value
    }

    override fun saveStringSet(key: String, value: Set<String>?) {
        stringSets[key] = value?.toSet()
    }

    override fun saveString(key: String, value: String?) {
        strings[key] = value
    }

    override fun getInt(key: String, defaultValue: Int): Int = ints[key] ?: defaultValue

    override fun getBoolean(key: String, defaultValue: Boolean): Boolean = bools[key] ?: defaultValue

    override fun getLong(key: String, defaultValue: Long): Long = longs[key] ?: defaultValue

    override fun getStringSet(key: String, defaultValue: Set<String>?): Set<String>? =
        stringSets[key]?.toSet() ?: defaultValue?.toSet()

    override fun getString(key: String, defaultValue: String?): String? =
        if (strings.containsKey(key)) strings[key] else defaultValue
}
