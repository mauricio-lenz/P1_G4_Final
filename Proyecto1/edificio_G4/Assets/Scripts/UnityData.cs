using System.Collections.Generic;
using UnityEngine;

public static class UnityData
{
    public static StructureData Structure;
    public static string ActiveCombo;

    public static Dictionary<string, List<DisplacementRecord>> DisplacementsByCombo;
    public static Dictionary<string, List<ElementForceRecord>> ElementForcesByCombo;

    private static Dictionary<string, PMCurveData> pmCurveLookup;
    private static Dictionary<string, SectionMaterialData> materialLookup;
    private static Dictionary<string, ComboInfo> comboLookup;

    public static void LoadData(StructureData data)
    {
        Structure = data;
        ActiveCombo = null;

        if (data.p1l4 == null)
        {
            DisplacementsByCombo = new Dictionary<string, List<DisplacementRecord>>();
            ElementForcesByCombo = new Dictionary<string, List<ElementForceRecord>>();
            pmCurveLookup = new Dictionary<string, PMCurveData>();
            materialLookup = new Dictionary<string, SectionMaterialData>();
            comboLookup = new Dictionary<string, ComboInfo>();
            return;
        }

        comboLookup = new Dictionary<string, ComboInfo>();
        if (data.p1l4.combinations != null)
        {
            foreach (ComboInfo c in data.p1l4.combinations)
            {
                if (c != null && !string.IsNullOrEmpty(c.name) && !comboLookup.ContainsKey(c.name))
                {
                    comboLookup[c.name] = c;
                }
            }
        }

        DisplacementsByCombo = new Dictionary<string, List<DisplacementRecord>>();
        if (data.p1l4.displacements != null)
        {
            foreach (DisplacementRecord d in data.p1l4.displacements)
            {
                if (string.IsNullOrEmpty(d.combo)) continue;
                if (!DisplacementsByCombo.ContainsKey(d.combo))
                {
                    DisplacementsByCombo[d.combo] = new List<DisplacementRecord>();
                }
                DisplacementsByCombo[d.combo].Add(d);
            }
        }

        ElementForcesByCombo = new Dictionary<string, List<ElementForceRecord>>();
        if (data.p1l4.elementForces != null)
        {
            foreach (ElementForceRecord f in data.p1l4.elementForces)
            {
                if (f == null || string.IsNullOrEmpty(f.combo)) continue;
                if (!ElementForcesByCombo.ContainsKey(f.combo))
                {
                    ElementForcesByCombo[f.combo] = new List<ElementForceRecord>();
                }
                ElementForcesByCombo[f.combo].Add(f);
            }
        }

        pmCurveLookup = new Dictionary<string, PMCurveData>();
        if (data.p1l4.pmCurves != null)
        {
            foreach (PMCurveData c in data.p1l4.pmCurves)
            {
                if (c != null && !string.IsNullOrEmpty(c.sectionId) && !pmCurveLookup.ContainsKey(c.sectionId))
                {
                    pmCurveLookup[c.sectionId] = c;
                }
            }
        }

        materialLookup = new Dictionary<string, SectionMaterialData>();
        if (data.p1l4.sectionMaterials != null)
        {
            foreach (SectionMaterialData m in data.p1l4.sectionMaterials)
            {
                if (m != null && !string.IsNullOrEmpty(m.sectionId) && !materialLookup.ContainsKey(m.sectionId))
                {
                    materialLookup[m.sectionId] = m;
                }
            }
        }
    }

    public static Vector3 GetNodeDisplacement(string combo, int nodeId)
    {
        if (string.IsNullOrEmpty(combo) || DisplacementsByCombo == null || !DisplacementsByCombo.TryGetValue(combo, out var list) || list == null)
        {
            return Vector3.zero;
        }

        foreach (DisplacementRecord d in list)
        {
            if (d.node == nodeId)
            {
                return new Vector3(d.ux, d.uz, d.uy);
            }
        }

        return Vector3.zero;
    }

    public static float[] GetElementForces(string combo, int elementId)
    {
        if (string.IsNullOrEmpty(combo) || ElementForcesByCombo == null || !ElementForcesByCombo.TryGetValue(combo, out var list) || list == null)
        {
            return null;
        }

        foreach (ElementForceRecord f in list)
        {
            if (f != null && f.id == elementId)
            {
                return f.f;
            }
        }

        return null;
    }

    public static PMCurveData GetPMCurve(string sectionId)
    {
        if (string.IsNullOrEmpty(sectionId) || pmCurveLookup == null) return null;
        return pmCurveLookup.TryGetValue(sectionId, out var curve) ? curve : null;
    }

    public static SectionMaterialData GetMaterial(string sectionId)
    {
        if (string.IsNullOrEmpty(sectionId) || materialLookup == null) return null;
        return materialLookup.TryGetValue(sectionId, out var mat) ? mat : null;
    }

    public static string GetComboLabel(string combo)
    {
        if (string.IsNullOrEmpty(combo)) return "sin combinacion activa";
        if (comboLookup != null && comboLookup.TryGetValue(combo, out var info) && info != null && !string.IsNullOrEmpty(info.label))
        {
            if (info.label.StartsWith(combo + ":")) return info.label;
            return $"{combo}: {info.label}";
        }
        return combo;
    }

    // ---------------------------------------------------------------
    // C14/C15/C16 · SUPERPOSICION EN VIVO DE CASOS BASE G/Q/EX/EY
    // Genera un combo sintetico "SUP" cuyas fuerzas y desplazamientos
    // son la combinacion lineal de los casos base con los lambdas de
    // los sliders. Todo el pipeline (diagramas, deformada, P-M) lee
    // por UnityData.ActiveCombo, asi que al activar SUP se actualiza
    // completo sin tocar DiagramController/PMPanel.
    // ---------------------------------------------------------------
    public static readonly string[] SuperpositionBaseCases = { "G", "Q", "EX", "EY" };
    public const string SuperpositionComboName = "SUP";
    public static float[] SuperpositionLambdas = { 1f, 1f, 1f, 1f };

    public static void ApplySuperposition(float lambdaG, float lambdaQ, float lambdaEX, float lambdaEY)
    {
        SuperpositionLambdas = new float[] { lambdaG, lambdaQ, lambdaEX, lambdaEY };

        if (ElementForcesByCombo == null)
        {
            ElementForcesByCombo = new Dictionary<string, List<ElementForceRecord>>();
        }

        // --- fuerzas por superposicion lineal de los casos base ---
        var supForces = new List<ElementForceRecord>();
        var firstBase = GetBaseForceList(SuperpositionBaseCases[0]);
        if (firstBase != null)
        {
            int[] ids = GetElementIds();
            foreach (int id in ids)
            {
                float[] sup = new float[12];
                for (int c = 0; c < SuperpositionBaseCases.Length; c++)
                {
                    float lambda = SuperpositionLambdas[c];
                    if (Mathf.Abs(lambda) < 0.0005f) continue;
                    float[] f = GetElementForces(SuperpositionBaseCases[c], id);
                    if (f == null) continue;
                    int n = Mathf.Min(f.Length, sup.Length);
                    for (int k = 0; k < n; k++) sup[k] += lambda * f[k];
                }
                supForces.Add(new ElementForceRecord { combo = SuperpositionComboName, id = id, f = sup });
            }
        }
        ElementForcesByCombo[SuperpositionComboName] = supForces;

        // --- desplazamientos por superposicion lineal de los casos base ---
        if (DisplacementsByCombo == null)
        {
            DisplacementsByCombo = new Dictionary<string, List<DisplacementRecord>>();
        }
        var supDisp = new List<DisplacementRecord>();
        if (DisplacementsByCombo.TryGetValue(SuperpositionBaseCases[0], out var baseDisp) && baseDisp != null)
        {
            foreach (DisplacementRecord d in baseDisp)
            {
                if (d == null) continue;
                float ux = 0f, uy = 0f, uz = 0f;
                for (int c = 0; c < SuperpositionBaseCases.Length; c++)
                {
                    float lambda = SuperpositionLambdas[c];
                    if (Mathf.Abs(lambda) < 0.0005f) continue;
                    Vector3 v = GetNodeDisplacement(SuperpositionBaseCases[c], d.node);
                    ux += lambda * v.x;
                    uy += lambda * v.y;
                    uz += lambda * v.z;
                }
                supDisp.Add(new DisplacementRecord { combo = SuperpositionComboName, node = d.node, ux = ux, uy = uy, uz = uz });
            }
        }
        DisplacementsByCombo[SuperpositionComboName] = supDisp;

        // --- etiqueta del combo sintetico ---
        if (comboLookup == null)
        {
            comboLookup = new Dictionary<string, ComboInfo>();
        }
        string label = $"Superposicion: {lambdaG:0.##}G + {lambdaQ:0.##}Q + {lambdaEX:0.##}EX + {lambdaEY:0.##}EY";
        comboLookup[SuperpositionComboName] = new ComboInfo
        {
            name = SuperpositionComboName,
            label = label,
            G = lambdaG,
            Q = lambdaQ,
            EX = lambdaEX,
            EY = lambdaEY
        };

        ActiveCombo = SuperpositionComboName;
    }

    private static List<ElementForceRecord> GetBaseForceList(string combo)
    {
        if (ElementForcesByCombo != null && ElementForcesByCombo.TryGetValue(combo, out var list)) return list;
        return null;
    }

    private static int[] GetElementIds()
    {
        var list = GetBaseForceList(SuperpositionBaseCases[0]);
        if (list == null || list.Count == 0) return new int[0];
        var ids = new List<int>();
        var seen = new HashSet<int>();
        foreach (ElementForceRecord r in list)
        {
            if (r != null && seen.Add(r.id)) ids.Add(r.id);
        }
        return ids.ToArray();
    }

    public static ComboInfo GetComboInfo(string combo)
    {
        if (string.IsNullOrEmpty(combo) || comboLookup == null) return null;
        return comboLookup.TryGetValue(combo, out var info) ? info : null;
    }
}
