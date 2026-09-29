using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Consola de diagnostico en pantalla (solo en builds de desarrollo):
/// muestra lo que cargo el viewer y los ultimos mensajes/errores del log,
/// para depurar en el telefono sin cable.
/// </summary>
public class DebugOverlay : MonoBehaviour
{
    private readonly List<string> lines = new List<string>();
    private bool expanded = true;
    private Vector2 scroll;
    private const int MaxLines = 40;

    private void OnEnable()
    {
        Application.logMessageReceived += OnLog;
    }

    private void OnDisable()
    {
        Application.logMessageReceived -= OnLog;
    }

    private void OnLog(string message, string stackTrace, LogType type)
    {
        string prefix = type == LogType.Error || type == LogType.Exception ? "[ERROR] "
                      : type == LogType.Warning ? "[AVISO] " : "";
        string line = prefix + message;
        if ((type == LogType.Exception || type == LogType.Error) && !string.IsNullOrEmpty(stackTrace))
        {
            line += "\n   " + stackTrace.Split('\n')[0];
        }
        lines.Add(line);
        if (lines.Count > MaxLines) lines.RemoveAt(0);
    }

    private string Summary()
    {
        StructureData s = UnityData.Structure;
        if (s == null) return "Estructura: NO cargada";
        int combos = UnityData.DisplacementsByCombo != null ? UnityData.DisplacementsByCombo.Count : 0;
        int forces = UnityData.ElementForcesByCombo != null ? UnityData.ElementForcesByCombo.Count : 0;
        var diagrams = FindAnyObjectByType<DiagramController>();
        return $"Nodos {s.nodes?.Length ?? 0} | elementos {s.elements?.Length ?? 0} | p1l4 {(s.p1l4 != null ? "si" : "NO")}\n" +
               $"Combos con desplazamientos {combos} | con fuerzas {forces} | activo {UnityData.ActiveCombo ?? "-"}\n" +
               $"Resultado {(diagrams != null ? diagrams.CurrentResultName() : "-")} | pantalla {Screen.width}x{Screen.height} " +
               $"dpi {Screen.dpi:0} escala UI {UiTheme.Scale:0.00}";
    }

    private void OnGUI()
    {
        UiTheme.ApplyScale();
        float w = Mathf.Min(560f, UiTheme.ScreenW * 0.45f);
        float x = UiTheme.ScreenW - w - UiTheme.SideM;
        if (!expanded)
        {
            if (GUI.Button(new Rect(x + w - 110f, UiTheme.ScreenH - 34f, 110f, 26f), "Diagnostico")) expanded = true;
            return;
        }
        float h = 230f;
        float y = UiTheme.ScreenH - h - 8f;
        UiTheme.GUIBox(new Rect(x, y, w, h), "DIAGNOSTICO (build de desarrollo)");
        if (GUI.Button(new Rect(x + w - 70f, y + 4f, 62f, 20f), "Ocultar")) expanded = false;
        GUI.Label(new Rect(x + 10f, y + 26f, w - 20f, 52f), Summary(), UiTheme.DimLabel);
        string text = string.Join("\n", lines);
        float contentH = Mathf.Max(120f, UiTheme.Label.CalcHeight(new GUIContent(text), w - 40f) + 8f);
        scroll = GUI.BeginScrollView(new Rect(x + 10f, y + 80f, w - 20f, h - 88f), scroll, new Rect(0f, 0f, w - 40f, contentH));
        GUI.Label(new Rect(0f, 0f, w - 40f, contentH), text, UiTheme.Label);
        GUI.EndScrollView();
    }
}
