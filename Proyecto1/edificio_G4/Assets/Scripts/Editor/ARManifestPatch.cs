using System.IO;
using UnityEditor.Android;
using UnityEngine;

/// <summary>
/// Semana 6 (AR): en el Galaxy S24 el sistema entregaba el giroscopio y el
/// acelerometro a la app cada 160 ms (~6 Hz) aunque ARCore pide 5 ms (200 Hz):
/// sin IMU el tracking visual-inercial deriva y no detecta planos.
/// Se agrega HIGH_SAMPLING_RATE_SENSORS (Android 12+) al manifiesto generado.
/// </summary>
public class ARManifestPatch : IPostGenerateGradleAndroidProject
{
    public int callbackOrder => 100;

    private const string Permission = "android.permission.HIGH_SAMPLING_RATE_SENSORS";

    public void OnPostGenerateGradleAndroidProject(string path)
    {
        string manifest = Path.Combine(path, "src", "main", "AndroidManifest.xml");
        if (!File.Exists(manifest)) return;
        string xml = File.ReadAllText(manifest);
        if (xml.Contains(Permission)) return;
        int close = xml.IndexOf('>', xml.IndexOf("<manifest"));
        xml = xml.Insert(close + 1, "\n  <uses-permission android:name=\"" + Permission + "\" />");
        File.WriteAllText(manifest, xml);
        Debug.Log("[ARManifestPatch] Permiso agregado: " + Permission);
    }
}
