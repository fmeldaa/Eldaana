package com.eldaana.app

import android.annotation.SuppressLint
import android.content.Intent
import android.os.Bundle
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.appcompat.app.AppCompatActivity

@SuppressLint("CustomSplashScreen")
class SplashActivity : AppCompatActivity() {

    companion object {
        const val PREFS        = "eldaana_prefs"
        const val KEY_LANG     = "app_lang"
        const val KEY_LANG_SET = "lang_set"
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val webView = WebView(this)
        setContentView(webView)

        webView.settings.javaScriptEnabled = true
        webView.settings.allowFileAccess   = true
        // Couleur beige-rosé Eldaana — visible AVANT que le HTML se charge
        webView.setBackgroundColor(0xFFC4A99A.toInt())
        webView.webViewClient = object : WebViewClient() {}
        webView.loadUrl("file:///android_asset/splash.html")

        val prefs   = getSharedPreferences(PREFS, MODE_PRIVATE)
        val langSet = prefs.getBoolean(KEY_LANG_SET, false)

        if (!langSet) {
            // Premier lancement → choix de langue après l'animation
            webView.postDelayed({ showLanguagePicker(webView) }, 2800)
        } else {
            // Déjà configuré → lancer l'app directement
            webView.postDelayed({ launchMain() }, 3500)
        }
    }

    private fun showLanguagePicker(webView: WebView) {
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
        overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
        finish()
    }
}
