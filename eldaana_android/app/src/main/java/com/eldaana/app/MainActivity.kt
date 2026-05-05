package com.eldaana.app

import android.annotation.SuppressLint
import android.app.AlarmManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.media.MediaRecorder
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import android.provider.Settings
import android.webkit.*
import android.view.Gravity
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.ImageButton
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import java.io.File
import java.io.OutputStreamWriter
import java.io.PrintWriter
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private val APP_URL = "https://app.eldaana.io/"


    // Upload fichiers
    private var fileUploadCallback: ValueCallback<Array<Uri>>? = null
    private var cameraPhotoUri: Uri? = null

    // Enregistrement vocal
    private var mediaRecorder: MediaRecorder? = null
    private var recordingFile: File? = null
    private var isRecording = false
    private var micButton: ImageButton? = null
    private var alarmButton: ImageButton? = null
    private var recordingStartTime = 0L

    // Navigation voix : URL en attente d'autorisation micro
    private var pendingVoiceUrl: String? = null

    // ─── Caméra ───────────────────────────────────────────────────────────────
    private fun createImageFile(): Uri {
        val ts   = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
        val file = File(externalCacheDir, "PHOTO_$ts.jpg")
        return FileProvider.getUriForFile(this, "$packageName.fileprovider", file)
    }

    // ─── onCreate ─────────────────────────────────────────────────────────────
    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // ── Forcer les barres système en beige rosé avant le chargement Streamlit ──
        // Évite la bande lavande visible pendant que le WebView charge app.eldaana.io.
        val beige = 0xFFC4A99A.toInt()
        window.statusBarColor     = beige
        window.navigationBarColor = beige
        window.decorView.setBackgroundColor(beige)

        // ── Canal notification réveil ──
        createWakeupChannel()

        // ── Permission micro (nécessaire pour show_mic_button Streamlit et Eldaana Voice) ──
        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this,
                arrayOf(android.Manifest.permission.RECORD_AUDIO), 99)
        }

        // ── Permission notifications (Android 13+) ──
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this,
                    arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), 100)
            }
        }

        // ── Permission alarmes exactes (Android 12+) ──
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val am = getSystemService(AlarmManager::class.java)
            if (!am.canScheduleExactAlarms()) {
                Toast.makeText(this,
                    "Autorise les alarmes exactes pour le réveil Eldaana",
                    Toast.LENGTH_LONG).show()
                val intent = Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM).apply {
                    data = Uri.parse("package:$packageName")
                }
                startActivity(intent)
            }
        }

        val root = FrameLayout(this)
        setContentView(root)

        // ── WebView ──
        webView = WebView(this)
        // Fond beige rosé visible AVANT que Streamlit se rende (évite le blanc/lavande)
        webView.setBackgroundColor(0xFFC4A99A.toInt())
        root.addView(webView, FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT
        ))

        webView.settings.apply {
            javaScriptEnabled                = true
            domStorageEnabled                = true
            mediaPlaybackRequiresUserGesture = false
            allowFileAccess                  = true
            allowContentAccess               = true
            cacheMode                        = WebSettings.LOAD_DEFAULT
            mixedContentMode                 = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            useWideViewPort                  = true
            loadWithOverviewMode             = true
            setSupportZoom(true)
            builtInZoomControls              = true
            displayZoomControls              = false
            userAgentString                  = "$userAgentString EldaanaApp/1.0"
        }

        // ── Interface JS → Android (lecture config réveil) ──
        webView.addJavascriptInterface(EldaanaAndroidBridge(), "EldaanaAndroid")

        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, req: WebResourceRequest): Boolean {
                val url = req.url.toString()
                // Google OAuth → ouvrir dans Chrome (Google bloque les WebViews depuis 2019)
                if (url.contains("accounts.google.com") ||
                    url.contains("oauth2.googleapis.com")) {
                    try {
                        startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                    } catch (_: Exception) {}
                    return true
                }
                // Stripe checkout/billing → ouvrir dans Chrome
                // (Stripe vérifie l'user-agent WebView et peut bloquer le paiement)
                if (url.contains("checkout.stripe.com") ||
                    url.contains("billing.stripe.com")) {
                    try {
                        startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)).apply {
                            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        })
                    } catch (_: Exception) {}
                    return true
                }
                // Quitter l'app principale → masquer les boutons overlay
                val isMainApp = url.contains("eldaana.io") ||
                                url.contains("streamlit.app") ||
                                url.contains("localhost")
                if (!isMainApp) {
                    runOnUiThread {
                        alarmButton?.visibility = android.view.View.GONE
                    }
                }
                return false  // tout le reste charge dans le WebView
            }

            override fun onPageFinished(view: WebView, url: String) {
                super.onPageFinished(view, url)
                // ── Mémoriser le uid dès qu'il apparaît dans l'URL ──────────────
                val uri = Uri.parse(url)
                val uid = uri.getQueryParameter("uid")
                if (!uid.isNullOrBlank()) {
                    getSharedPreferences("eldaana_prefs", MODE_PRIVATE)
                        .edit().putString("user_uid", uid).apply()
                }

                // ── Retour depuis Stripe sans uid → recharger avec uid sauvegardé ──
                // Stripe redirige vers l'app principale mais sans les params Android.
                // Sans uid, Streamlit crée une nouvelle session sans profil → Voice bloqué.
                val isMainApp = url.contains("eldaana.io") ||
                                url.contains("streamlit.app") ||
                                url.contains("localhost")
                if (isMainApp && uid.isNullOrBlank()) {
                    val savedUid = getSharedPreferences("eldaana_prefs", MODE_PRIVATE)
                        .getString("user_uid", "") ?: ""
                    if (savedUid.isNotBlank() && !url.contains("uid=")) {
                        val prefs = getSharedPreferences(SplashActivity.PREFS, MODE_PRIVATE)
                        val lang  = prefs.getString(SplashActivity.KEY_LANG, "fr") ?: "fr"
                        view.postDelayed({
                            view.loadUrl("${APP_URL}?lang=$lang&uid=$savedUid&platform=android")
                        }, 300)
                        return
                    }
                }

                // Streamlit rend ses composants via React après le chargement HTML
                // → on réessaie toutes les 3s pendant 30s jusqu'à trouver le div
                scheduleWakeupConfigRead(view, attempts = 10, delayMs = 3000)

                // ── Afficher/masquer les boutons + injecter intercept micro ──────
                if (isMainApp) {
                    // Délai 3s : Streamlit (React) prend du temps à rendre son UI
                    // après que le HTML est reçu — on attend qu'il soit visible
                    view.postDelayed({
                        alarmButton?.visibility = android.view.View.VISIBLE
                        // Intercepter "Appuyer et parler" → enregistrement natif Android
                        // (WebRTC getUserMedia() est bloqué sur certains WebViews)
                        injectMicButtonIntercept(view)
                    }, 3000)
                    // Re-injecter à 8s au cas où Streamlit re-render après hydration
                    view.postDelayed({ injectMicButtonIntercept(view) }, 8000)
                } else {
                    // Page externe (Voice, Stripe…) → cacher immédiatement
                    alarmButton?.visibility = android.view.View.GONE
                }
            }
        }

        // ── Interface JS → Navigation Eldaana Voice ──────────────────────────────
        webView.addJavascriptInterface(object {
            @android.webkit.JavascriptInterface
            fun openVoice(url: String) {
                runOnUiThread {
                    // Google OAuth → Chrome obligatoire (Google bloque Error 403 dans WebView)
                    if (url.contains("accounts.google.com") || url.contains("oauth2.googleapis.com")) {
                        try {
                            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)).apply {
                                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                            })
                        } catch (_: Exception) {}
                    } else {
                        // On quitte l'app principale → masquer les boutons overlay immédiatement
                        alarmButton?.visibility = android.view.View.GONE

                        // Libérer le MediaRecorder natif s'il est actif
                        if (isRecording) {
                            try { mediaRecorder?.stop() } catch (_: Exception) {}
                            mediaRecorder?.release()
                            mediaRecorder = null
                            isRecording = false
                            recordingFile = null
                            micButton?.clearColorFilter()
                        }

                        webView.loadUrl(url)
                    }
                }
            }
            @android.webkit.JavascriptInterface
            fun goBack() {
                runOnUiThread {
                    // Retour sur l'app principale → réafficher le bouton overlay
                    alarmButton?.visibility = android.view.View.VISIBLE

                    val prefs    = getSharedPreferences(SplashActivity.PREFS, MODE_PRIVATE)
                    val lang     = prefs.getString(SplashActivity.KEY_LANG, "fr") ?: "fr"
                    val savedUid = getSharedPreferences("eldaana_prefs", MODE_PRIVATE)
                        .getString("user_uid", "") ?: ""
                    val uidParam = if (savedUid.isNotBlank()) "&uid=$savedUid" else ""
                    webView.loadUrl("${APP_URL}?lang=$lang$uidParam&platform=android")
                }
            }
        }, "EldaanaNav")

        webView.webChromeClient = object : WebChromeClient() {
            override fun onPermissionRequest(request: PermissionRequest) {
                request.grant(request.resources)
            }

            override fun onShowFileChooser(
                webView: WebView,
                filePathCallback: ValueCallback<Array<Uri>>,
                fileChooserParams: FileChooserParams
            ): Boolean {
                fileUploadCallback?.onReceiveValue(null)
                fileUploadCallback = filePathCallback

                android.app.AlertDialog.Builder(this@MainActivity)
                    .setTitle("Ajouter une photo")
                    .setItems(arrayOf("📷  Prendre une photo", "🖼️  Choisir dans la galerie")) { _, which ->
                        when (which) {
                            0 -> {
                                if (ContextCompat.checkSelfPermission(
                                        this@MainActivity, android.Manifest.permission.CAMERA)
                                    != PackageManager.PERMISSION_GRANTED) {
                                    ActivityCompat.requestPermissions(this@MainActivity,
                                        arrayOf(android.Manifest.permission.CAMERA), 98)
                                    fileUploadCallback?.onReceiveValue(null)
                                    fileUploadCallback = null
                                    return@setItems
                                }
                                val photoUri = createImageFile()
                                cameraPhotoUri = photoUri
                                val intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE).apply {
                                    putExtra(MediaStore.EXTRA_OUTPUT, photoUri)
                                    addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
                                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                                }
                                @Suppress("DEPRECATION")
                                startActivityForResult(intent, 102)
                            }
                            1 -> {
                                val intent = Intent(Intent.ACTION_GET_CONTENT).apply {
                                    type = "image/*"
                                    putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true)
                                }
                                @Suppress("DEPRECATION")
                                startActivityForResult(intent, 101)
                            }
                        }
                    }
                    .setOnCancelListener {
                        fileUploadCallback?.onReceiveValue(null)
                        fileUploadCallback = null
                    }
                    .show()
                return true
            }
        }

        // ── Chargement initial ──
        if (savedInstanceState != null) {
            webView.restoreState(savedInstanceState)
        } else {
            loadAppUrl(intent)
        }

        // ── Premier lancement : proposer de configurer le réveil ──
        val prefs = getSharedPreferences("eldaana_prefs", MODE_PRIVATE)
        if (!prefs.getBoolean("wakeup_enabled", false)) {
            // Délai pour laisser l'app se charger d'abord
            webView.postDelayed({ showFirstAlarmSetup() }, 4000)
        }

        // ── Boutons overlay : créés CACHÉS, visibles seulement quand l'app est chargée ──
        val dp   = resources.displayMetrics.density
        val size = (48 * dp).toInt()

        // Bouton réveil (cloche) — bas gauche
        alarmButton = ImageButton(this).apply {
            setImageResource(android.R.drawable.ic_lock_idle_alarm)
            setBackgroundColor(Color.WHITE)
            elevation = 8 * dp
            alpha     = 0.95f
            setColorFilter(Color.parseColor("#C9A84C"))
            setOnClickListener { showAlarmTimePicker() }
            visibility = android.view.View.GONE   // caché jusqu'au chargement
        }
        val alarmLp = FrameLayout.LayoutParams(size, size).apply {
            gravity      = Gravity.BOTTOM or Gravity.START
            bottomMargin = (14 * dp).toInt()
            leftMargin   = (12 * dp).toInt()
        }
        root.addView(alarmButton, alarmLp)

    }


    // ─── Chargement URL app ───────────────────────────────────────────────────

    private fun loadAppUrl(intent: Intent?) {
        val prefs    = getSharedPreferences(SplashActivity.PREFS, MODE_PRIVATE)
        val lang     = prefs.getString(SplashActivity.KEY_LANG, "fr") ?: "fr"
        val savedUid = getSharedPreferences("eldaana_prefs", MODE_PRIVATE)
            .getString("user_uid", "") ?: ""
        val uidParam = if (savedUid.isNotBlank()) "&uid=$savedUid" else ""
        val isWakeup = intent?.getBooleanExtra("WAKEUP", false) ?: false
        val url = when {
            isWakeup -> "${APP_URL}?wakeup=1&lang=$lang$uidParam&platform=android"
            else     -> "${APP_URL}?lang=$lang$uidParam&platform=android"
        }
        webView.loadUrl(url)
    }

    // ─── Retour deep link eldaana:// après Google OAuth dans Chrome ──────────

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        val data = intent.data ?: return
        if (data.scheme == "eldaana") {
            val uid   = data.getQueryParameter("uid")   ?: ""
            val code  = data.getQueryParameter("code")  ?: ""
            val state = data.getQueryParameter("state") ?: ""

            if (uid.isNotBlank()) {
                getSharedPreferences("eldaana_prefs", MODE_PRIVATE)
                    .edit().putString("user_uid", uid).apply()
            }

            val prefs    = getSharedPreferences(SplashActivity.PREFS, MODE_PRIVATE)
            val lang     = prefs.getString(SplashActivity.KEY_LANG, "fr") ?: "fr"
            val savedUid = getSharedPreferences("eldaana_prefs", MODE_PRIVATE)
                .getString("user_uid", "") ?: ""
            val uidParam = if (savedUid.isNotBlank()) "&uid=$savedUid" else ""

            // ── Callback OAuth Google : code + state dans le deep link ──────────
            // Quand redirect_uri = "eldaana://callback", Chrome redirige ici après
            // l'authentification Google. On recharge l'app avec le code en param
            // pour que Streamlit puisse l'échanger contre un token.
            if (code.isNotBlank()) {
                val codeEnc  = Uri.encode(code)
                val stateEnc = Uri.encode(state)
                webView.loadUrl(
                    "${APP_URL}?lang=$lang$uidParam&platform=android" +
                    "&code=$codeEnc&state=$stateEnc"
                )
                return
            }

            webView.loadUrl("${APP_URL}?lang=$lang$uidParam&platform=android")
        }
    }

    // ─── Sélecteur d'heure réveil ─────────────────────────────────────────────

    private fun showFirstAlarmSetup() {
        android.app.AlertDialog.Builder(this)
            .setTitle("⏰ Réveil Eldaana")
            .setMessage("À quelle heure veux-tu que je te réveille chaque matin ?")
            .setPositiveButton("Configurer") { _, _ -> showAlarmTimePicker() }
            .setNegativeButton("Plus tard", null)
            .show()
    }

    private fun showAlarmTimePicker() {
        val prefs  = getSharedPreferences("eldaana_prefs", MODE_PRIVATE)
        val hour   = prefs.getInt("wakeup_hour", 7)
        val minute = prefs.getInt("wakeup_min",  0)
        val prenom = prefs.getString("prenom", "") ?: ""

        android.app.TimePickerDialog(this, { _, h, m ->
            AlarmScheduler.schedule(this, h, m, prenom)
            Toast.makeText(this,
                "⏰ Réveil Eldaana programmé à ${h}h${m.toString().padStart(2,'0')}",
                Toast.LENGTH_LONG).show()
        }, hour, minute, true).show()
    }

    // ─── Lecture config réveil avec retry ────────────────────────────────────

    private fun scheduleWakeupConfigRead(view: WebView, attempts: Int, delayMs: Long) {
        if (attempts <= 0) return
        val js = """
            (function() {
                var cfg = document.getElementById('eldaana-config');
                if (cfg) {
                    var t = cfg.getAttribute('data-wakeup') || '';
                    var p = cfg.getAttribute('data-prenom') || '';
                    if (t && window.EldaanaAndroid) {
                        window.EldaanaAndroid.setWakeupTime(t, p);
                        return 'ok:' + t;
                    }
                }
                return '';
            })();
        """.trimIndent()

        view.postDelayed({
            view.evaluateJavascript(js) { result ->
                // Si pas trouvé (résultat vide ou null), on réessaie
                if (result.isNullOrBlank() || result == "\"\"" || result == "null") {
                    scheduleWakeupConfigRead(view, attempts - 1, delayMs)
                }
                // Sinon l'alarme a été programmée → on arrête
            }
        }, delayMs)
    }

    // ─── Scroll vers le bas (appelé après injection du texte) ───────────────

    private fun scheduleScrollToBottom(view: WebView) {
        // Scroller à intervalles pour suivre le streaming de la réponse
        val js = """
            (function() {
                var el = document.querySelector('[data-testid="stAppViewContainer"]')
                      || document.querySelector('.main')
                      || document.documentElement;
                if (el) el.scrollTop = el.scrollHeight;
                window.scrollTo(0, document.body.scrollHeight);
            })();
        """.trimIndent()
        // 1s, 2s, 4s, 7s, 12s — couvre toute la durée du streaming
        for (delay in listOf(1000L, 2000L, 4000L, 7000L, 12000L)) {
            view.postDelayed({ view.evaluateJavascript(js, null) }, delay)
        }
    }

    // ─── Canal notification réveil ────────────────────────────────────────────

    private fun createWakeupChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val nm = getSystemService(NotificationManager::class.java)
            if (nm.getNotificationChannel(AlarmReceiver.CHANNEL_ID) != null) return
            val channel = NotificationChannel(
                AlarmReceiver.CHANNEL_ID,
                "Réveil Eldaana",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Notification de réveil personnalisée"
                enableVibration(true)
                enableLights(true)
            }
            nm.createNotificationChannel(channel)
        }
    }

    // ─── JS Bridge : reçoit heure réveil depuis Streamlit ────────────────────

    inner class EldaanaAndroidBridge {

        /** Appelé depuis le JS injecté quand l'utilisateur tape "Appuyer et parler" */
        @android.webkit.JavascriptInterface
        fun startNativeMic() {
            runOnUiThread { toggleRecording() }
        }

        /** Ouvre la page Voice dans le WebView */
        @android.webkit.JavascriptInterface
        fun openVoice(url: String) {
            runOnUiThread {
                alarmButton?.visibility = android.view.View.GONE
                // Libérer le MediaRecorder s'il est actif (libère le micro)
                if (isRecording) {
                    try { mediaRecorder?.stop() } catch (_: Exception) {}
                    mediaRecorder?.release()
                    mediaRecorder = null
                    isRecording = false
                    recordingFile = null
                    micButton?.clearColorFilter()
                }
                webView.loadUrl(url)
            }
        }

        /**
         * Démarre l'enregistrement natif Android depuis la page Voice.
         * Contourne getUserMedia() (bloqué dans le WebView sur certains appareils).
         */
        @android.webkit.JavascriptInterface
        fun startVoiceCapture() {
            runOnUiThread {
                if (ContextCompat.checkSelfPermission(
                        this@MainActivity, android.Manifest.permission.RECORD_AUDIO)
                    != PackageManager.PERMISSION_GRANTED) {
                    ActivityCompat.requestPermissions(this@MainActivity,
                        arrayOf(android.Manifest.permission.RECORD_AUDIO), 96)
                } else {
                    startRecording()
                }
            }
        }

        /**
         * Arrête l'enregistrement, lit le fichier M4A et l'injecte dans la page Voice
         * via receiveNativeAudio(base64, 'mp4').
         */
        @android.webkit.JavascriptInterface
        fun stopVoiceCapture() {
            runOnUiThread { stopAndSendToWebView() }
        }

        @android.webkit.JavascriptInterface
        fun setWakeupTime(time: String, prenom: String) {
            if (time.isBlank()) return
            val parts  = time.split(":")
            val hour   = parts.getOrNull(0)?.toIntOrNull() ?: return
            val minute = parts.getOrNull(1)?.toIntOrNull() ?: 0
            AlarmScheduler.schedule(applicationContext, hour, minute, prenom)
            runOnUiThread {
                Toast.makeText(
                    applicationContext,
                    "⏰ Réveil programmé à ${hour}h${minute.toString().padStart(2,'0')}",
                    Toast.LENGTH_LONG
                ).show()
            }
        }
    }

    // ─── Bridge audio page Voice → WebSocket ────────────────────────────────────

    /**
     * Arrête le MediaRecorder, encode l'audio M4A en base64 (thread de fond),
     * puis appelle receiveNativeAudio(b64, 'mp4') dans la page Voice.
     */
    private fun stopAndSendToWebView() {
        if (!isRecording) return

        mediaRecorder?.apply {
            try { stop() } catch (_: Exception) {}
            release()
        }
        mediaRecorder = null
        isRecording = false
        micButton?.clearColorFilter()

        val file = recordingFile ?: return

        Thread {
            try {
                if (!file.exists() || file.length() == 0L) {
                    runOnUiThread {
                        webView.evaluateJavascript(
                            "setStatus('⚠️ Audio vide — parle plus fort','error')", null)
                    }
                    return@Thread
                }
                val bytes  = file.readBytes()
                val b64    = android.util.Base64.encodeToString(bytes, android.util.Base64.NO_WRAP)
                runOnUiThread {
                    webView.evaluateJavascript("receiveNativeAudio('$b64','mp4')", null)
                }
            } catch (e: Exception) {
                val msg = e.message?.replace("'", "\\'") ?: "erreur"
                runOnUiThread {
                    webView.evaluateJavascript("setStatus('❌ Erreur audio: $msg','error')", null)
                }
            }
        }.start()
    }

    // ─── Enregistrement vocal + Whisper ───────────────────────────────────────

    private fun toggleRecording() {
        if (isRecording) {
            stopAndTranscribe()
        } else {
            startRecording()
        }
    }

    private fun startRecording() {
        // 1. Vérifier permission
        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this,
                arrayOf(android.Manifest.permission.RECORD_AUDIO), 99)
            return
        }

        // 2. Vérifier que la clé API est configurée
        if (BuildConfig.OPENAI_KEY.isBlank() || BuildConfig.OPENAI_KEY == "REMPLACE_PAR_TA_CLE_ICI") {
            Toast.makeText(this,
                "Clé OpenAI manquante dans local.properties", Toast.LENGTH_LONG).show()
            return
        }

        // 3. Démarrer l'enregistrement
        val file = File(cacheDir, "eldaana_voice.m4a")
        recordingFile = file

        @Suppress("DEPRECATION")
        mediaRecorder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S)
            MediaRecorder(this) else MediaRecorder()

        mediaRecorder!!.apply {
            // VOICE_RECOGNITION = optimisé pour la parole, meilleur que MIC
            setAudioSource(MediaRecorder.AudioSource.VOICE_RECOGNITION)
            setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
            setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
            setAudioSamplingRate(44100)
            setAudioEncodingBitRate(128000)
            setOutputFile(file.absolutePath)
            try {
                prepare()
                start()
            } catch (e: Exception) {
                Toast.makeText(this@MainActivity,
                    "Erreur démarrage micro: ${e.message}", Toast.LENGTH_LONG).show()
                release()
                mediaRecorder = null
                return
            }
        }

        isRecording = true
        recordingStartTime = System.currentTimeMillis()
        micButton?.setColorFilter(Color.RED)
        Toast.makeText(this, "🎤 Je t'écoute… Appuie à nouveau pour envoyer", Toast.LENGTH_LONG).show()
    }

    private fun stopAndTranscribe() {
        mediaRecorder?.apply {
            try { stop() } catch (_: Exception) {}
            release()
        }
        mediaRecorder = null
        isRecording   = false
        micButton?.setColorFilter(Color.parseColor("#7B2FBE"))

        val file = recordingFile
        if (file == null || !file.exists() || file.length() < 500L) {
            Toast.makeText(this, "Enregistrement vide, réessaie", Toast.LENGTH_SHORT).show()
            return
        }

        Toast.makeText(this, "⏳ Transcription en cours…", Toast.LENGTH_SHORT).show()
        micButton?.alpha = 0.4f  // feedback visuel discret pendant la transcription

        Thread {
            try {
                Thread.sleep(300)
                val (text, _) = whisperTranscribeDebug(file, BuildConfig.OPENAI_KEY)
                runOnUiThread {
                    micButton?.alpha = 0.95f
                    if (text.isNotBlank()) {
                        injectTextAndSubmit(text)
                    } else {
                        Toast.makeText(this, "Rien compris — réessaie", Toast.LENGTH_SHORT).show()
                    }
                }
            } catch (e: Exception) {
                runOnUiThread {
                    Toast.makeText(this, "Erreur: ${e.message?.take(80)}", Toast.LENGTH_LONG).show()
                }
            }
        }.start()
    }

    // ─── Appel OpenAI Whisper (debug) ─────────────────────────────────────────

    private fun whisperTranscribeDebug(file: File, apiKey: String): Pair<String, String> {
        val boundary = "Boundary${System.currentTimeMillis()}"
        val CRLF     = "\r\n"

        val conn = (URL("https://api.openai.com/v1/audio/transcriptions")
            .openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            doOutput      = true
            connectTimeout = 15_000
            readTimeout    = 30_000
            setRequestProperty("Authorization",  "Bearer $apiKey")
            setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
        }

        conn.outputStream.use { os ->
            val pw = PrintWriter(OutputStreamWriter(os, "UTF-8"), true)
            pw.append("--$boundary$CRLF")
            pw.append("Content-Disposition: form-data; name=\"model\"$CRLF$CRLF")
            pw.append("whisper-1$CRLF").flush()
            pw.append("--$boundary$CRLF")
            pw.append("Content-Disposition: form-data; name=\"language\"$CRLF$CRLF")
            pw.append("fr$CRLF").flush()
            pw.append("--$boundary$CRLF")
            pw.append("Content-Disposition: form-data; name=\"file\"; filename=\"voice.m4a\"$CRLF")
            pw.append("Content-Type: audio/mp4$CRLF$CRLF").flush()
            file.inputStream().use { it.copyTo(os) }
            os.flush()
            pw.append(CRLF)
            pw.append("--$boundary--$CRLF").flush()
        }

        val code     = conn.responseCode
        val response = (if (code == 200) conn.inputStream else conn.errorStream)
            ?.bufferedReader()?.readText() ?: "NO RESPONSE"
        conn.disconnect()

        if (code != 200) return Pair("", "HTTP $code: $response")

        val text = Regex("\"text\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"")
            .find(response)?.groupValues?.get(1) ?: ""
        return Pair(text, response)
    }

    // ─── Appel OpenAI Whisper ─────────────────────────────────────────────────

    private fun whisperTranscribe(file: File, apiKey: String): String {
        val boundary = "Boundary${System.currentTimeMillis()}"
        val CRLF     = "\r\n"

        val conn = (URL("https://api.openai.com/v1/audio/transcriptions")
            .openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            doOutput      = true
            connectTimeout = 15_000
            readTimeout    = 30_000
            setRequestProperty("Authorization",  "Bearer $apiKey")
            setRequestProperty("Content-Type",
                "multipart/form-data; boundary=$boundary")
        }

        conn.outputStream.use { os ->
            val pw = PrintWriter(OutputStreamWriter(os, "UTF-8"), true)

            // champ model
            pw.append("--$boundary$CRLF")
            pw.append("Content-Disposition: form-data; name=\"model\"$CRLF$CRLF")
            pw.append("whisper-1$CRLF").flush()

            // champ language
            pw.append("--$boundary$CRLF")
            pw.append("Content-Disposition: form-data; name=\"language\"$CRLF$CRLF")
            pw.append("fr$CRLF").flush()

            // fichier audio
            pw.append("--$boundary$CRLF")
            pw.append("Content-Disposition: form-data; name=\"file\"; filename=\"voice.m4a\"$CRLF")
            pw.append("Content-Type: audio/mp4$CRLF$CRLF").flush()
            file.inputStream().use { it.copyTo(os) }
            os.flush()
            pw.append(CRLF)
            pw.append("--$boundary--$CRLF").flush()
        }

        val code     = conn.responseCode
        val response = (if (code == 200) conn.inputStream else conn.errorStream)
            ?.bufferedReader()?.readText() ?: ""
        conn.disconnect()

        if (code != 200) throw Exception("HTTP $code: $response")

        // {"text":"..."}
        return Regex("\"text\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"")
            .find(response)?.groupValues?.get(1) ?: ""
    }

    // ─── Interception du bouton "Appuyer et parler" → enregistrement natif ────
    // Approche : event delegation sur le document de chaque iframe (stable même
    // si React recrée le bouton), MutationObserver léger pour les nouveaux iframes.

    private fun injectMicButtonIntercept(view: WebView) {
        val js = """
            (function eldaanaMicIntercept() {

                // Attache un listener de délégation sur un document (pas sur le bouton)
                // → résiste aux re-renders React qui détruisent/recréent le bouton
                function interceptDoc(doc) {
                    if (!doc || doc._eldaanaMicReady) return;
                    doc._eldaanaMicReady = true;
                    doc.addEventListener('click', function(e) {
                        if (!e.isTrusted) return;   // ignorer clics synthétiques React
                        var node = e.target;
                        // Remonter jusqu'au premier BUTTON parent
                        while (node && node !== doc.body) {
                            if (node.tagName === 'BUTTON') {
                                var txt = (node.textContent || node.innerText || '').toLowerCase();
                                if (txt.indexOf('parler') >= 0) {
                                    e.preventDefault();
                                    e.stopImmediatePropagation();
                                    // EldaanaAndroid est sur la fenêtre principale
                                    var bridge = window.EldaanaAndroid
                                              || (window.top && window.top.EldaanaAndroid);
                                    if (bridge) bridge.startNativeMic();
                                    return;
                                }
                                break;
                            }
                            node = node.parentElement;
                        }
                    }, true);
                }

                function attachToFrame(frame) {
                    // Essayer immédiatement + au chargement si pas encore prêt
                    try { interceptDoc(frame.contentDocument); } catch(e) {}
                    frame.addEventListener('load', function() {
                        try {
                            interceptDoc(frame.contentDocument);
                            // Chercher les iframes imbriquées
                            frame.contentDocument.querySelectorAll('iframe')
                                .forEach(function(f2) { attachToFrame(f2); });
                        } catch(e) {}
                    });
                }

                // Attacher au document principal et à tous les iframes existants
                interceptDoc(document);
                document.querySelectorAll('iframe').forEach(function(f) { attachToFrame(f); });

                // Observer UNIQUEMENT les ajouts d'iframes (pas subtree) → très léger
                if (!window._eldaanaMicObs) {
                    window._eldaanaMicObs = new MutationObserver(function(muts) {
                        muts.forEach(function(m) {
                            m.addedNodes.forEach(function(n) {
                                if (n.nodeType !== 1) return;
                                if (n.tagName === 'IFRAME') {
                                    attachToFrame(n);
                                } else {
                                    n.querySelectorAll && n.querySelectorAll('iframe')
                                        .forEach(function(f) { attachToFrame(f); });
                                }
                            });
                        });
                    });
                    // childList + subtree pour trouver les iframes à n'importe quel niveau
                    // mais le callback ne fait QUE chercher des IFRAME → coût minimal
                    window._eldaanaMicObs.observe(document.body,
                        {childList: true, subtree: true});
                }
            })();
        """.trimIndent()
        view.evaluateJavascript(js, null)
    }

    // ─── Injection dans le chat Streamlit ─────────────────────────────────────

    private fun injectTextAndSubmit(text: String) {
        val safe = text.replace("\\", "\\\\").replace("'", "\\'").replace("\"", "\\\"")

        // Streamlit rend son UI dans des iframes — il faut chercher dans tous les contextes
        val js = """
            (function() {
                function tryInject(doc) {
                    var ta = doc.querySelector('textarea[data-testid="stChatInputTextArea"]')
                            || doc.querySelector('textarea');
                    if (!ta) return false;

                    ta.focus();

                    // Une seule méthode : execCommand uniquement.
                    // Utiliser React setter + execCommand en même temps génère 2 événements
                    // 'input' → React soumet le formulaire 2 fois → double réponse.
                    ta.select();
                    doc.execCommand('selectAll', false, null);
                    doc.execCommand('insertText', false, '$safe');

                    setTimeout(function() {
                        var btn = doc.querySelector('button[data-testid="stChatInputSubmitButton"]');
                        if (btn) {
                            btn.removeAttribute('disabled');
                            btn.click();
                        } else {
                            ta.dispatchEvent(new KeyboardEvent('keydown',
                                {key:'Enter', keyCode:13, bubbles:true}));
                        }
                    }, 800);
                    return true;
                }

                // 1. Essayer le document principal
                if (tryInject(document)) return;

                // 2. Chercher dans tous les iframes (Streamlit en utilise plusieurs)
                var frames = document.querySelectorAll('iframe');
                for (var i = 0; i < frames.length; i++) {
                    try {
                        var fdoc = frames[i].contentDocument
                                || frames[i].contentWindow.document;
                        if (tryInject(fdoc)) return;
                    } catch(e) {}
                }

                // 3. Chercher en profondeur (iframes dans iframes)
                var allFrames = document.querySelectorAll('iframe');
                for (var j = 0; j < allFrames.length; j++) {
                    try {
                        var win = allFrames[j].contentWindow;
                        var subFrames = win.document.querySelectorAll('iframe');
                        for (var k = 0; k < subFrames.length; k++) {
                            try {
                                if (tryInject(subFrames[k].contentDocument)) return;
                            } catch(e) {}
                        }
                    } catch(e) {}
                }
            })();
        """.trimIndent()

        webView.postDelayed({
            webView.evaluateJavascript(js, null)
        }, 300)

        // Suivre la réponse qui streame en scrollant vers le bas
        scheduleScrollToBottom(webView)
    }

    // ─── Permissions ──────────────────────────────────────────────────────────

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<String>, grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        when (requestCode) {
            96 -> {
                // Permission accordée depuis startVoiceCapture (page Voice)
                if (grantResults.isNotEmpty() &&
                    grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                    startRecording()
                } else {
                    webView.evaluateJavascript(
                        "setStatus('❌ Permission micro refusée','error')", null)
                }
            }
            99 -> {
                // Permission micro accordée — ne PAS démarrer l'enregistrement automatiquement.
                // L'utilisateur appuiera lui-même sur le bouton 🎤 quand il voudra parler.
            }
            97 -> {
                // Permission micro pour la navigation vers la page vocale
                val url = pendingVoiceUrl
                pendingVoiceUrl = null
                if (grantResults.isNotEmpty() &&
                    grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                    // Permission accordée → naviguer
                    if (url != null) webView.loadUrl(url)
                } else {
                    // Permission refusée → ouvrir les paramètres Android
                    Toast.makeText(this,
                        "Active le micro dans Paramètres > Eldaana > Micro",
                        Toast.LENGTH_LONG).show()
                    val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                        data = Uri.parse("package:$packageName")
                    }
                    startActivity(intent)
                }
            }
        }
    }

    // ─── Caméra / Galerie ─────────────────────────────────────────────────────

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        @Suppress("DEPRECATION")
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == 101) {
            if (resultCode == RESULT_OK) {
                val uris = mutableListOf<Uri>()
                data?.clipData?.let { for (i in 0 until it.itemCount) uris.add(it.getItemAt(i).uri) }
                if (uris.isEmpty()) data?.data?.let { uris.add(it) }
                fileUploadCallback?.onReceiveValue(uris.toTypedArray())
            } else fileUploadCallback?.onReceiveValue(null)
            fileUploadCallback = null
            return
        }
        if (requestCode == 102) {
            if (resultCode == RESULT_OK && cameraPhotoUri != null)
                fileUploadCallback?.onReceiveValue(arrayOf(cameraPhotoUri!!))
            else
                fileUploadCallback?.onReceiveValue(null)
            fileUploadCallback = null
            cameraPhotoUri     = null
            return
        }
    }

    // ─── Lifecycle ────────────────────────────────────────────────────────────

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        webView.saveState(outState)
    }

    override fun onDestroy() {
        if (isRecording) {
            mediaRecorder?.apply { try { stop() } catch (_: Exception) {} ; release() }
        }
        super.onDestroy()
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (webView.canGoBack()) webView.goBack()
        else @Suppress("DEPRECATION") super.onBackPressed()
    }
}
