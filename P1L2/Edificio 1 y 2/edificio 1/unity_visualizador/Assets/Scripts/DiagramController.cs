using System.Collections.Generic;
using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

public class DiagramController : MonoBehaviour
{
    private enum DiagramMode
    {
        None,
        Axial,
        Shear,
        Moment
    }

    public float diagramScale = 0.45f;

    private readonly List<ElementSelectable> elements = new List<ElementSelectable>();
    private readonly List<GameObject> diagramObjects = new List<GameObject>();
    private DiagramMode currentMode = DiagramMode.None;
    private float currentMaxValue = 1f;

    public void Initialize(List<ElementSelectable> selectables)
    {
        elements.Clear();
        elements.AddRange(selectables);
        ShowDiagram(DiagramMode.None);
    }

    private void Update()
    {
        if (PressedKey(KeyCode.Alpha0))
        {
            ShowDiagram(DiagramMode.None);
        }
        if (PressedKey(KeyCode.Alpha1))
        {
            ShowDiagram(DiagramMode.Axial);
        }
        if (PressedKey(KeyCode.Alpha2))
        {
            ShowDiagram(DiagramMode.Shear);
        }
        if (PressedKey(KeyCode.Alpha3))
        {
            ShowDiagram(DiagramMode.Moment);
        }
    }

    private bool PressedKey(KeyCode key)
    {
#if ENABLE_INPUT_SYSTEM
        Keyboard keyboard = Keyboard.current;
        if (keyboard == null)
        {
            return false;
        }

        if (key == KeyCode.Alpha0) return keyboard.digit0Key.wasPressedThisFrame;
        if (key == KeyCode.Alpha1) return keyboard.digit1Key.wasPressedThisFrame;
        if (key == KeyCode.Alpha2) return keyboard.digit2Key.wasPressedThisFrame;
        if (key == KeyCode.Alpha3) return keyboard.digit3Key.wasPressedThisFrame;
        return false;
#else
        return Input.GetKeyDown(key);
#endif
    }

    private void ShowDiagram(DiagramMode mode)
    {
        currentMode = mode;
        ClearDiagram();

        if (mode == DiagramMode.None)
        {
            return;
        }

        currentMaxValue = GetMaxValue(mode);

        foreach (ElementSelectable element in elements)
        {
            if (element.data == null)
            {
                continue;
            }

            if (mode == DiagramMode.Moment && element.data.type != "viga")
            {
                continue;
            }

            CreateElementDiagram(element, mode);
        }
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
            points[i] = basePoint + offsetDirection * value / currentMaxValue * ScaleFor(mode);
        }

        GameObject lineObject = new GameObject($"Diagrama_{mode}_E{element.data.id}");
        lineObject.transform.SetParent(transform);
        LineRenderer line = lineObject.AddComponent<LineRenderer>();
        line.positionCount = points.Length;
        line.SetPositions(points);
        line.startWidth = 0.035f;
        line.endWidth = 0.035f;
        line.material = CreateMaterial(GetColor(mode));
        diagramObjects.Add(lineObject);

        CreateLabel(points[0], GetValue(element.data, mode, 0f, length), lineObject.transform);
        CreateLabel(points[segments], GetValue(element.data, mode, 1f, length), lineObject.transform);
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

            if (mode == DiagramMode.Moment && element.data.type != "viga")
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
        if (mode == DiagramMode.Axial) return diagramScale * 0.75f;
        if (mode == DiagramMode.Shear) return diagramScale * 0.9f;
        return diagramScale;
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
        return Color.magenta;
    }

    private void CreateLabel(Vector3 position, float value, Transform parent)
    {
        GameObject labelObject = new GameObject("ValorDiagrama");
        labelObject.transform.SetParent(parent);
        labelObject.transform.position = position + Vector3.up * 0.12f;

        TextMesh text = labelObject.AddComponent<TextMesh>();
        text.text = value.ToString("0.0");
        text.characterSize = 0.18f;
        text.anchor = TextAnchor.MiddleCenter;
        text.color = Color.white;
    }

    private Material CreateMaterial(Color color)
    {
        Shader shader = Shader.Find("Sprites/Default");
        Material material = new Material(shader);
        material.color = color;
        return material;
    }

    private void ClearDiagram()
    {
        foreach (GameObject diagramObject in diagramObjects)
        {
            Destroy(diagramObject);
        }

        diagramObjects.Clear();
    }

    private void OnGUI()
    {
        string text = "Diagramas: 0 ocultar | 1 axial | 2 corte | 3 momento";
        text += $"\nActual: {currentMode}";
        if (currentMode == DiagramMode.Moment)
        {
            text += " | solo vigas";
        }
        GUI.Box(new Rect(20, 180, 360, 55), text);
    }
}
