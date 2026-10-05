using System.IO;
using UnityEngine;

/// <summary>
/// Ejecuta un script de Proyecto1/scripts en segundo plano (python o py) y
/// avisa cuando termina. Solo disponible en el editor o en PC.
/// La salida se lee en forma asincrona (un script que imprime mucho no se
/// bloquea con el bufer lleno) y la ultima linea queda en <see cref="LastLine"/>.
/// </summary>
public class PythonJob
{
    public string OutputPath { get; private set; }
    public string Error { get; private set; }
    public bool Running => process != null;
    /// Ultima linea impresa por el script (progreso).
    public string LastLine => lastLine;
    public float Elapsed => process != null ? Time.unscaledTime - startTime : lastElapsed;

    /// true en el editor y en PC (hay Python/OpenSees); false en celular.
    public static bool Available
    {
        get
        {
#if UNITY_EDITOR || UNITY_STANDALONE
            return ScriptsDir != null;
#else
            return false;
#endif
        }
    }

#if UNITY_EDITOR || UNITY_STANDALONE
    private System.Diagnostics.Process process;
#else
    private object process;
#endif
    private float startTime;
    private float lastElapsed;
    private volatile string lastLine = "";
    private readonly System.Text.StringBuilder errors = new System.Text.StringBuilder();

    private static string scriptsDir;
    private static bool scriptsSearched;

    /// Carpeta Proyecto1/scripts: se busca hacia arriba desde los datos de la app
    /// (editor: edificio_G4/Assets; build de Windows: Builds/Windows/..._Data).
    public static string ScriptsDir
    {
        get
        {
            if (scriptsSearched) return scriptsDir;
            scriptsSearched = true;
            var dir = new DirectoryInfo(Application.dataPath);
            for (int i = 0; i < 7 && dir != null; i++, dir = dir.Parent)
            {
                string candidate = Path.Combine(dir.FullName, "scripts");
                if (File.Exists(Path.Combine(candidate, "carga_viva_sismo.py"))) { scriptsDir = candidate; break; }
            }
            return scriptsDir;
        }
    }

    /// Carpeta Proyecto1 (padre de scripts), o null.
    public static string ProjectRoot => ScriptsDir != null ? Path.GetDirectoryName(ScriptsDir) : null;

    public static string ScriptPath(string scriptName)
    {
        return ScriptsDir != null ? Path.Combine(ScriptsDir, scriptName) : scriptName;
    }

    /// Lanza "python -X utf8 script args --out <salida>". Devuelve false si no se pudo.
    public bool Start(string scriptName, string args, string outName)
    {
        Error = null;
        lastLine = "";
        errors.Length = 0;
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
                var p = new System.Diagnostics.Process { StartInfo = info };
                p.OutputDataReceived += (_, e) => { if (!string.IsNullOrWhiteSpace(e.Data)) lastLine = e.Data.Trim(); };
                p.ErrorDataReceived += (_, e) => { if (!string.IsNullOrWhiteSpace(e.Data)) lock (errors) errors.AppendLine(e.Data); };
                p.Start();
                p.BeginOutputReadLine();
                p.BeginErrorReadLine();
                process = p;
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
        process.WaitForExit();   // vacia las lecturas asincronas pendientes
        lastElapsed = Time.unscaledTime - startTime;
        int exitCode = process.ExitCode;
        process = null;
        if (exitCode != 0 || !File.Exists(OutputPath))
        {
            string err;
            lock (errors) err = errors.ToString().Trim();
            string[] lines = err.Split('\n');
            // el exportador valida las entradas y sale con codigo 2: "ERROR de validacion: ..."
            string validation = System.Array.Find(lines, l => l.StartsWith("ERROR"));
            if (validation != null) Error = validation.Trim();
            else Error = $"Error en Python (codigo {exitCode}): " + (err.Length == 0 ? (lastLine.Length > 0 ? lastLine : "sin salida") : lines[lines.Length - 1].Trim());
            if (File.Exists(OutputPath)) File.Delete(OutputPath);   // nunca cargar un resultado de una corrida fallida
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
