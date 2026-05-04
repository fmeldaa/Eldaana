package com.eldaana.app

import android.annotation.SuppressLint
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.WindowCompat

@SuppressLint("CustomSplashScreen")
class SplashActivity : AppCompatActivity() {

    companion object {
        const val PREFS        = "eldaana_prefs"
        const val KEY_LANG     = "app_lang"
        const val KEY_LANG_SET = "lang_set"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // ── Edge-to-edge : le layout couvre les barres système ────────────────
        WindowCompat.setDecorFitsSystemWindows(window, false)
        window.statusBarColor     = Color.parseColor("#C4A99A")
        window.navigationBarColor = Color.parseColor("#C4A99A")
        window.decorView.setBackgroundColor(Color.parseColor("#C4A99A"))

        // ── Layout natif XML — plus de WebView ────────────────────────────────
        setContentView(R.layout.activity_splash)

        val prefs   = getSharedPreferences(PREFS, MODE_PRIVATE)
        val langSet = prefs.getBoolean(KEY_LANG_SET, false)

        if (!langSet) {
            // Premier lancement → dialogue de choix de langue après l'animation
            window.decorView.postDelayed({ showLanguagePicker() }, 2800)
        } else {
            // Déjà configuré → lancer l'app directement
            window.decorView.postDelayed({ launchMain() }, 2500)
        }
    }

    private fun showLanguagePicker() {
        val options = arrayOf("🇫🇷  Français", "🇬🇧  English")
        android.app.AlertDialog.Builder(this)
            .setTitle("Choisissez votre langue  /  Choose your language")
            .setItems(options) { _, which ->
                val lang = if (which == 0) "fr" else "en"
                getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                    .putString(KEY_LANG, lang)
                    .putBoolean(KEY_LANG_SET, true)
                    .apply()
                launchMain()
            }
            .setCancelable(false)
            .show()
    }

    private fun launchMain() {
        startActivity(Intent(this, MainActivity::class.java))
        @Suppress("DEPRECATION")
        overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
        finish()
    }
}
