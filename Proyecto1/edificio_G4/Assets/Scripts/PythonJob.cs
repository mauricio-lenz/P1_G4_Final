using System.IO;
using UnityEngine;

/// <summary>
/// Ejecuta un script de Proyecto1/scripts en segundo plano (python o py) y
/// avisa cuando termina. Solo disponible en el editor o en PC.
/// </summary>
public class PythonJob
{
    public string OutputPath { get; private set; }
    public string Error { get; private set; }
    public bool Running => process != null;

#if UNITY_EDITOR || UNITY_STANDALONE
    private System.Diagnostics.Process process;
#else
    private object process;
#endif
    private float startTime;

    public static string ScriptPath(string scriptName)
    {
        return Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "scripts", scriptName));
    }

    /// Lanza "python -X utf8 script args --out <salida>". Devuelve false si no se pudo.
    public bool Start(string scriptName, string args, string outName)
    {
        Error = null;
#if UNITY_EDITOR || UNITY_STANDALONE
        string script = ScriptPath(scriptName);
        if (!File.Exists(script))
        {
            Error = "No encontre scripts/" + scriptName;
            return false;
        }
        OutputPath = Path.Combine(Application.temporaryCachePath, outName);
        if (File.Exists(OutputPath)) File.Delete(OutputPath);
        foreach (string exe in new[] { "python", "py" })
        {
            try
            {
                var info = new System.Diagnostics.ProcessStartInfo
                {
                    FileName = exe,
                    Arguments = $"-X utf8 \"{script}\" {args} --out \"{OutputPath}\"",
                    WorkingDirectory = Path.GetDirectoryName(script),
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true
                };
                process = System.Diagnostics.Process.Start(info);
                startTime = Time.unscaledTime;
                return true;
            }
            catch (System.Exception)
            {
                process = null;
            }
        }
        Error = "No se pudo ejecutar Python (python/py en el PATH).";
        return false;
#else
        Error = "Requiere Python: solo disponible en el editor o en PC.";
        return false;
#endif
    }

    /// Llamar en Update. Devuelve true una vez, cuando el proceso termino.
    public bool Poll(float timeoutSeconds = 120f)
    {
#if UNITY_EDITOR || UNITY_STANDALONE
        if (process == null) return false;
        if (!process.HasExited)
        {
            if (Time.unscaledTime - startTime > timeoutSeconds)
            {
                try { process.Kill(); } catch (System.Exception) { }
                process = null;
                Error = "Tiempo de calculo excedido.";
                return true;
            }
            return false;
        }
        process.StandardOutput.ReadToEnd();
        string err = process.StandardError.ReadToEnd();
        process = null;
        if (!File.Exists(OutputPath))
        {
            Error = "Error en Python: " + (string.IsNullOrEmpty(err) ? "sin salida" : err.Trim().Split('\n')[0]);
        }
        return true;
#else
        return false;
#endif
    }

    public void Kill()
    {
#if UNITY_EDITOR || UNITY_STANDALONE
        if (process != null && !process.HasExited)
        {
            try { process.Kill(); } catch (System.Exception) { }
        }
        process = null;
#endif
    }
}
