using UnityEditor;
using UnityEditor.PackageManager;
using UnityEditor.PackageManager.Requests;
using UnityEngine;

/// <summary>
/// Semana 6 (AR): instala AR Foundation + ARCore XR Plugin + XR Plugin Management
/// con la version recomendada para este editor.
/// Consola: Unity.exe -batchmode -projectPath edificio_G4 -executeMethod ARPackageInstaller.Install
/// (sin -quit: el script cierra Unity al terminar).
/// </summary>
public static class ARPackageInstaller
{
    private static readonly string[] Packages =
    {
        "com.unity.xr.arfoundation",
        "com.unity.xr.arcore",
        "com.unity.xr.management",
    };

    private static AddAndRemoveRequest request;

    [MenuItem("MCOC/AR/Instalar paquetes AR")]
    public static void Install()
    {
        Debug.Log("[ARPackageInstaller] Instalando: " + string.Join(", ", Packages));
        request = Client.AddAndRemove(Packages, null);
        EditorApplication.update += Progress;
    }

    private static void Progress()
    {
        if (request == null || !request.IsCompleted) return;
        EditorApplication.update -= Progress;
        if (request.Status == StatusCode.Success)
        {
            foreach (var p in request.Result)
            {
                if (p.name.StartsWith("com.unity.xr") || p.name.StartsWith("com.unity.inputsystem"))
                {
                    Debug.Log($"[ARPackageInstaller] OK {p.name} {p.version}");
                }
            }
            if (Application.isBatchMode) EditorApplication.Exit(0);
        }
        else
        {
            Debug.LogError("[ARPackageInstaller] ERROR: " + (request.Error != null ? request.Error.message : "desconocido"));
            if (Application.isBatchMode) EditorApplication.Exit(1);
        }
    }
}
