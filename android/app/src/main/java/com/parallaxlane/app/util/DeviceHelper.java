package com.parallaxlane.app.util;

import android.annotation.SuppressLint;
import android.content.Context;
import android.provider.Settings;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import java.nio.charset.StandardCharsets;
import java.security.KeyPairGenerator;
import java.security.KeyStore;
import java.security.MessageDigest;
import java.security.PrivateKey;
import java.security.Signature;
import java.security.spec.ECGenParameterSpec;

// Identifies this phone to the server and signs the exam start request with a key stored in the Android Keystore.
public class DeviceHelper {

    private static final String KEY_ALIAS = "parallaxlane_device_key";

    // Returns the SHA256 hash of the Android ID as hex text so the real ID is never sent.
    @SuppressLint("HardwareIds")
    public static String getDeviceId(Context context) {
        String androidId = Settings.Secure.getString(context.getContentResolver(), Settings.Secure.ANDROID_ID);
        try {
            byte[] hash = MessageDigest.getInstance("SHA-256").digest(androidId.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder();
            for (byte b : hash) {
                hex.append(String.format("%02x", b));
            }
            return hex.toString();
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    // Returns the public key as Base64 text for device registration, creates the key pair the first time.
    public static synchronized String getPublicKey() throws Exception {
        KeyStore keyStore = openKeyStore();
        if (!keyStore.containsAlias(KEY_ALIAS)) {
            createKey();
        }
        byte[] encoded = keyStore.getCertificate(KEY_ALIAS).getPublicKey().getEncoded();
        return Base64.encodeToString(encoded, Base64.NO_WRAP);
    }

    // Signs the text the server sends before an exam starts and returns the signature as Base64 text.
    public static synchronized String sign(String text) throws Exception {
        PrivateKey privateKey = (PrivateKey) openKeyStore().getKey(KEY_ALIAS, null);
        Signature signature = Signature.getInstance("SHA256withECDSA");
        signature.initSign(privateKey);
        signature.update(text.getBytes(StandardCharsets.UTF_8));
        return Base64.encodeToString(signature.sign(), Base64.NO_WRAP);
    }

    // Creates an EC key pair inside the Android Keystore, the private key can never be copied out of the phone.
    private static void createKey() throws Exception {
        KeyPairGenerator generator = KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, "AndroidKeyStore");
        generator.initialize(new KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_SIGN)
                .setAlgorithmParameterSpec(new ECGenParameterSpec("secp256r1"))
                .setDigests(KeyProperties.DIGEST_SHA256)
                .build());
        generator.generateKeyPair();
    }

    // Opens the Android Keystore.
    private static KeyStore openKeyStore() throws Exception {
        KeyStore keyStore = KeyStore.getInstance("AndroidKeyStore");
        keyStore.load(null);
        return keyStore;
    }
}
