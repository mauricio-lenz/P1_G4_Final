using System.Collections.Generic;
using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

[ExecuteAlways]
public class DiagramController : MonoBehaviour
{
    private enum DiagramMode
    {
        None,
        Axial,
        Shear,
        Moment,
        InteractionPM
    }

    public float diagramScale = 1.3f;
    public float axialMultiplier = 0.9f;
    public float shearMultiplier = 1.0f;
    public float momentMultiplier = 1.2f;
    public float diagramBaseOffset = 0.06f;

    private readonly List<ElementSelectable> elements = new List<ElementSelectable>();
    private readonly List<GameObject> diagramObjects = new List<GameObject>();
    private DiagramMode currentMode = DiagramMode.None;
    private float currentMaxValue = 1f;
    private Semana3UnityResults semana3Results;

    public void Initialize(List<ElementSelectable> selectables)
    {
        elements.Clear();
        elements.AddRange(selectables);
        LoadSemana3Results();
        ShowDiagram(DiagramMode.None);
        Debug.Log($"[DiagramController] listo con {elements.Count} elementos");
    }

    private void Update()
    {
        if (Application.isPlaying && PressedKey(KeyCode.Alpha0))
        {
            ShowDiagram(DiagramMode.None);
        }
        if (Application.isPlaying && PressedKey(KeyCode.Alpha1))
        {
            ShowDiagram(DiagramMode.Axial);
        }
        if (Application.isPlaying && PressedKey(KeyCode.Alpha2))
        {
            ShowDiagram(DiagramMode.Shear);
        }
        if (Application.isPlaying && PressedKey(KeyCode.Alpha3))
        {
            ShowDiagram(DiagramMode.Moment);
        }
        if (Application.isPlaying && PressedKey(KeyCode.Alpha4))
        {
            ShowDiagram(DiagramMode.InteractionPM);
        }
    }

    private bool PressedKey(KeyCode key)
    {
#if ENABLE_INPUT_SYSTEM
        Keyboard keyboard = Keyboard.current;
        if (keyboard != null)
        {
            if (key == KeyCode.Alpha0) return keyboard.digit0Key.wasPressedThisFrame;
            if (key == KeyCode.Alpha1) return keyboard.digit1Key.wasPressedThisFrame;
            if (key == KeyCode.Alpha2) return keyboard.digit2Key.wasPressedThisFrame;
            if (key == KeyCode.Alpha3) return keyboard.digit3Key.wasPressedThisFrame;
            if (key == KeyCode.Alpha4) return keyboard.digit4Key.wasPressedThisFrame;
        }
#endif
        return Input.GetKeyDown(key);
    }

    private void ShowDiagram(DiagramMode mode)
    {
        currentMode = mode;
        ClearDiagram();

        if (mode == DiagramMode.None || mode == DiagramMode.InteractionPM)
        {
            return;
        }

        currentMaxValue = GetMaxValue(mode);
        int created = 0;
        int edificio1 = 0;
        int edificio2 = 0;

        foreach (ElementSelectable element in elements)
        {
            if (element.data == null)
            {
                continue;
            }

            if ((mode == DiagramMode.Moment || mode == DiagramMode.Shear) && element.data.type != "viga")
            {
                continue;
            }

            CreateElementDiagram(element, mode);
            created++;
            if (element.data.sourceBuilding == "edificio_2")
            {
                edificio2++;
            }
            else
            {
                edificio1++;
            }
        }

        Debug.Log($"[DiagramController] modo {mode}: {created} diagramas (edificio_1: {edificio1}, edificio_2: {edificio2}), max={currentMaxValue:0.###}");
    }

    private void CreateElementDiagram(ElementSelectable element, DiagramMode mode)
    {
        int segments = 12;
        Vector3[] points = new Vector3[segments + 1];
        Vector3 axis = element.endPoint - element.startPoint;
        Vector3 offsetDirection = GetOffsetDirection(axis, mode);
        float length = axis.magnitude;

        for (int i = 0; i <= segments; i++)
        {
            float t = i / (float)segments;
            Vector3 basePoint = Vector3.Lerp(element.startPoint, element.endPoint, t);
            float value = GetValue(element.data, mode, t, length);
            points[i] = basePoint + offsetDirection * (diagramBaseOffset + value / currentMaxValue * ScaleFor(mode));
        }

        GameObject lineObject = new GameObject($"Diagrama_{mode}_E{element.data.id}");
        lineObject.transform.SetParent(transform);
        lineObject.hideFlags = HideFlags.DontSave;
        LineRenderer line = lineObject.AddComponent<LineRenderer>();
        line.positionCount = points.Length;
        line.SetPositions(points);
        line.startWidth = 0.08f;
        line.endWidth = 0.08f;
        line.useWorldSpace = true;
        line.material = CreateMaterial(GetColor(mode));
        diagramObjects.Add(lineObject);

        CreateLabel(points[0], GetValue(element.data, mode, 0f, length), UnitFor(mode), lineObject.transform);
        CreateLabel(points[segments / 2], GetValue(element.data, mode, 0.5f, length), UnitFor(mode), lineObject.transform);
        CreateLabel(points[segments], GetValue(element.data, mode, 1f, length), UnitFor(mode), lineObject.transform);
    }

    private float GetMaxValue(DiagramMode mode)
    {
        float maxValue = 0.001f;

        foreach (ElementSelectable element in elements)
        {
            if (element.data == null)
            {
                continue;
            }

            if ((mode == DiagramMode.Moment || mode == DiagramMode.Shear) && element.data.type != "viga")
            {
                continue;
            }

            int segments = 20;
            for (int i = 0; i <= segments; i++)
            {
                float t = i / (float)segments;
                float length = (element.endPoint - element.startPoint).magnitude;
                maxValue = Mathf.Max(maxValue, Mathf.Abs(GetValue(element.data, mode, t, length)));
            }
        }

        return maxValue;
    }

    private float GetValue(ElementData data, DiagramMode mode, float t, float length)
    {
        if (data == null)
        {
            return 0f;
        }

        if (mode == DiagramMode.Axial)
        {
            return Mathf.Lerp(data.axialI, data.axialJ, t);
        }

        if (mode == DiagramMode.Shear)
        {
            return Mathf.Lerp(data.shearI, data.shearJ, t);
        }

        float linearMoment = Mathf.Lerp(data.momentI, data.momentJ, t);
        float spanMoment = Mathf.Abs(data.uniformLoad) * length * length * t * (1f - t) / 2f;
        return linearMoment + spanMoment;
    }

    private float ScaleFor(DiagramMode mode)
    {
        if (mode == DiagramMode.Axial) return diagramScale * axialMultiplier;
        if (mode == DiagramMode.Shear) return diagramScale * shearMultiplier;
        return diagramScale * momentMultiplier;
    }

    private Vector3 GetOffsetDirection(Vector3 axis, DiagramMode mode)
    {
        if (mode == DiagramMode.Moment && Mathf.Abs(axis.normalized.y) < 0.2f)
        {
            return Vector3.up;
        }

        Vector3 direction = Vector3.Cross(axis.normalized, Vector3.forward).normalized;
        if (direction.sqrMagnitude < 0.01f)
        {
            direction = Vector3.right;
        }

        return direction;
    }

    private Color GetColor(DiagramMode mode)
    {
        if (mode == DiagramMode.Axial) return Color.red;
        if (mode == DiagramMode.Shear) return new Color(1f, 0.55f, 0f);
        if (mode == DiagramMode.InteractionPM) return Color.green;
        return Color.magenta;
    }

    private string UnitFor(DiagramMode mode)
    {
        if (mode == DiagramMode.Moment) return " kN*m";
        return " kN";
    }

    private void CreateLabel(Vector3 position, float value, string unit, Transform parent)
    {
        GameObject labelObject = new GameObject("ValorDiagrama");
        labelObject.transform.SetParent(parent);
        labelObject.hideFlags = HideFlags.DontSave;
        labelObject.transform.position = position + Vector3.up * 0.18f;

        TextMesh text = labelObject.AddComponent<TextMesh>();
        text.text = value.ToString("0.0") + unit;
        text.characterSize = 0.2f;
        text.anchor = TextAnchor.MiddleCenter;
        text.color = Color.white;
    }

    private Material CreateMaterial(Color color)
    {
        Shader shader = Shader.Find("Custom/AlwaysOnTopLine");
        if (shader == null)
        {
            shader = Shader.Find("Unlit/Color");
        }
        if (shader == null)
        {
            shader = Shader.Find("Sprites/Default");
        }
        if (shader == null)
        {
            shader = Shader.Find("Standard");
        }

        Material material = new Material(shader);
        material.color = color;
        if (shader.name == "Custom/AlwaysOnTopLine")
        {
            material.renderQueue = 5000;
        }
        else
        {
            material.renderQueue = 4000;
        }

        return material;
    }

    private void ClearDiagram()
    {
        foreach (GameObject diagramObject in diagramObjects)
        {
            if (Application.isPlaying)
            {
                Destroy(diagramObject);
            }
            else
            {
                DestroyImmediate(diagramObject);
            }
        }

        diagramObjects.Clear();
    }

    private void OnGUI()
    {
        GUILayout.BeginArea(new Rect(20, Screen.height - 122f, 390, 102), GUI.skin.box);
        GUILayout.Label("Diagramas OpenSees");
        GUILayout.BeginHorizontal();
        if (GUILayout.Button("0 Ocultar")) ShowDiagram(DiagramMode.None);
        if (GUILayout.Button("1 Axial")) ShowDiagram(DiagramMode.Axial);
        if (GUILayout.Button("2 Corte")) ShowDiagram(DiagramMode.Shear);
        if (GUILayout.Button("3 Momento")) ShowDiagram(DiagramMode.Moment);
        GUILayout.EndHorizontal();
        if (GUILayout.Button("4 Curva P-M HA")) ShowDiagram(DiagramMode.InteractionPM);
        GUILayout.Label($"Actual: {currentMode}");
        GUILayout.EndArea();
        string useHint = Application.isPlaying
            ? "Teclas 1-4 o botones para cambiar de diagrama."
            : "Modo edicion: usa los botones (las teclas requieren Play).";
        GUI.Label(new Rect(20, Screen.height - 40f, 420, 24), useHint);

        if (currentMode == DiagramMode.Moment)
        {
            GUI.Label(new Rect(420, Screen.height - 112f, 320, 24), "Momento My: valores OpenSees + qL2/8 en vigas");
        }
        if (currentMode == DiagramMode.InteractionPM)
        {
            DrawPMPanel();
        }
    }

    private void LoadSemana3Results()
    {
        TextAsset resultsJson = Resources.Load<TextAsset>("semana3_resultados_unity");
        if (resultsJson == null)
        {
            semana3Results = null;
            return;
        }

        semana3Results = JsonUtility.FromJson<Semana3UnityResults>(resultsJson.text);
    }

    private void DrawPMPanel()
    {
        Rect rect = new Rect(Mathf.Max(20f, Screen.width - 520f), Mathf.Max(285f, Screen.height - 330f), 500f, 310f);
        GUILayout.BeginArea(rect, GUI.skin.box);
        if (semana3Results == null || semana3Results.pmPoints == null || semana3Results.pmPoints.Length == 0)
        {
            semana3Results = DefaultSemana3Results();
            GUILayout.Label("Usando puntos P-M por defecto de Semana 3.");
        }

        GUILayout.Label(semana3Results.capacityTitle);
        GUILayout.Label($"Seccion: {semana3Results.sectionId} | {semana3Results.b_m:0.00} x {semana3Results.h_m:0.00} m");
        GUILayout.Label($"fc'={semana3Results.fc_MPa:0.0} MPa | fy={semana3Results.fy_MPa:0.0} MPa | barras={semana3Results.steelBars} | rho={semana3Results.rho_percent:0.###}%");
        GUILayout.Label($"Barra: diam. {semana3Results.barDiameter_mm:0.0} mm | As={semana3Results.barArea_mm2:0.0} mm2 | Ast={semana3Results.Ast_mm2:0.0} mm2");
        DrawPMChart(new Rect(18f, 82f, 250f, 175f));
        GUILayout.Space(185f);
        foreach (PMPoint point in semana3Results.pmPoints)
        {
            GUILayout.Label($"{point.label}: P={point.P_kN:0.0} kN, M={point.M_kN_m:0.0} kN*m");
        }
        GUILayout.Label("Interpretacion: aumenta M con P moderado; cerca de Po baja hacia M~0.");
        GUILayout.EndArea();
    }

    private void DrawPMChart(Rect chartRect)
    {
        GUI.Box(chartRect, "");
        float maxM = 1f;
        float maxP = Mathf.Max(1f, semana3Results.Po_kN);
        foreach (PMPoint point in semana3Results.pmPoints)
        {
            maxM = Mathf.Max(maxM, point.M_kN_m);
            maxP = Mathf.Max(maxP, point.P_kN);
        }

        Vector2 previous = Vector2.zero;
        for (int i = 0; i < semana3Results.pmPoints.Length; i++)
        {
            PMPoint point = semana3Results.pmPoints[i];
            float x = chartRect.x + 30f + point.M_kN_m / maxM * (chartRect.width - 45f);
            float y = chartRect.y + chartRect.height - 25f - point.P_kN / maxP * (chartRect.height - 45f);
            Vector2 current = new Vector2(x, y);
            if (i > 0)
            {
                DrawGuiLine(previous, current, Color.green, 2f);
            }
            GUI.Label(new Rect(x - 5f, y - 8f, 80f, 18f), "o");
            previous = current;
        }

        GUI.Label(new Rect(chartRect.x + 8f, chartRect.y + 5f, 120f, 20f), "P [kN]");
        GUI.Label(new Rect(chartRect.x + chartRect.width - 90f, chartRect.y + chartRect.height - 22f, 80f, 20f), "M [kN*m]");
    }

    private void DrawGuiLine(Vector2 start, Vector2 end, Color color, float width)
    {
        Matrix4x4 matrix = GUI.matrix;
        Color oldColor = GUI.color;
        GUI.color = color;
        Vector2 delta = end - start;
        float angle = Mathf.Atan2(delta.y, delta.x) * Mathf.Rad2Deg;
        GUIUtility.RotateAroundPivot(angle, start);
        GUI.DrawTexture(new Rect(start.x, start.y, delta.magnitude, width), Texture2D.whiteTexture);
        GUI.matrix = matrix;
        GUI.color = oldColor;
    }

    private Semana3UnityResults DefaultSemana3Results()
    {
        return new Semana3UnityResults
        {
            capacityTitle = "Parte D - Capacidad HA COL70/70_FIBER",
            sectionId = "COL70/70_FIBER",
            b_m = 0.70f,
            h_m = 0.70f,
            fc_MPa = 25.0f,
            fy_MPa = 420.0f,
            steelBars = 8,
            barArea_m2 = 0.000491f,
            barArea_mm2 = 490.9f,
            barDiameter_mm = 25.0f,
            Ast_m2 = 0.003927f,
            Ast_mm2 = 3927.0f,
            rho_percent = 0.801f,
            Po_kN = 11978.4f,
            interpretation = "Al aumentar P de compresion desde cero, aumenta inicialmente la capacidad a momento; cerca de Po baja hacia M~0.",
            pmPoints = new PMPoint[]
            {
                new PMPoint { label = "A) Compresion pura", P_kN = 11978.388f, M_kN_m = 0.0f, phi_1_m = 0.0f },
                new PMPoint { label = "B) Balance", P_kN = 5020.930f, M_kN_m = 1270.813f, phi_1_m = 0.0f },
                new PMPoint { label = "C) Ultima falla ductil", P_kN = 2825.149f, M_kN_m = 1130.504f, phi_1_m = 0.0f },
                new PMPoint { label = "D) Flexion pura", P_kN = 0.0f, M_kN_m = 513.175f, phi_1_m = 0.0f },
                new PMPoint { label = "E) Traccion pura", P_kN = -1649.336f, M_kN_m = 0.0f, phi_1_m = 0.0f }
            }
        };
    }
}

[System.Serializable]
public class Semana3UnityResults
{
    public string capacityTitle;
    public string sectionId;
    public float b_m;
    public float h_m;
    public float fc_MPa;
    public float fy_MPa;
    public int steelBars;
    public float barArea_m2;
    public float barArea_mm2;
    public float barDiameter_mm;
    public float Ast_m2;
    public float Ast_mm2;
    public float rho_percent;
    public float Po_kN;
    public string interpretation;
    public PMPoint[] pmPoints;
}

[System.Serializable]
public class PMPoint
{
    public string label;
    public float P_kN;
    public float M_kN_m;
    public float phi_1_m;
}
