using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Semana 6 · Fase 4: resultados de OpenSees del elemento seleccionado.
/// Todo viene precalculado en el PC (carga_viva_sismo.py -> exportar_resultados_unity.py
/// -> Resources/estructura_p1l4_unity.json); el telefono solo lee, interpola
/// esfuerzos internos (UnityData.InternalForcesAt) y transforma coordenadas.
/// </summary>
public class ARResultsPanel : MonoBehaviour
{
    private const float PanelW = 400f;
    private ARStructure structure;
    private readonly List<ElementData> sector = new List<ElementData>();
    private string combo = "C1";
    private static readonly string[] Combos = { "G", "Q", "EX", "EY", "C1", "C2", "C3" };

    private void Start()
    {
        structure = FindAnyObjectByType<ARStructure>();
        if (structure != null) structure.Rebuilt += OnRebuilt;
    }

    private void OnRebuilt()
    {
        sector.Clear();
        foreach (ElementData e in UnityData.Structure.elements)
        {
            if (structure.InSector(e) && !UnityData.IsAnalysisOnly(e)) sector.Add(e);
        }
        sector.Sort((a, b) => string.CompareOrdinal(a.type, b.type) != 0 ? string.CompareOrdinal(a.type, b.type) : a.id.CompareTo(b.id));
        if (structure.Selected == null) Select(structure.FindByTag(ARStructure.AnchorTag));
        else structure.RefreshColors();
    }

    private void Select(ElementData e)
    {
        structure.Selected = e;
        structure.RefreshColors();
    }

    public static bool IsOverPanel(Vector2 screenPos)
    {
        return screenPos.x / UiTheme.Scale > UiTheme.ScreenW - UiTheme.SideM - PanelW - 4f;
    }

    private void Update()
    {
        if (structure == null || structure.ModelRoot == null) return;
        if (Input.touchCount != 1 || Input.GetTouch(0).phase != UnityEngine.TouchPhase.Began) return;
        Vector2 pos = Input.GetTouch(0).position;
        if (IsOverPanel(pos) || pos.x / UiTheme.Scale < UiTheme.SideM + 480f) return;
        Camera cam = Camera.main;
        if (cam == null) return;
        // los planos AR tambien tienen collider: se toma la barra mas cercana
        RaycastHit[] hits = Physics.RaycastAll(cam.ScreenPointToRay(pos), 300f);
        System.Array.Sort(hits, (a, b) => a.distance.CompareTo(b.distance));
        foreach (RaycastHit hit in hits)
        {
            var tag = hit.collider.GetComponent<ARElementTag>();
            if (tag != null) { Select(tag.element); break; }
        }
    }

    private void OnGUI()
    {
        if (structure == null || structure.ModelRoot == null) return;
        UiTheme.ApplyScale();
        float x = UiTheme.ScreenW - UiTheme.SideM - PanelW, y = UiTheme.SideM, w = PanelW;
        float h = UiTheme.ScreenH - 2f * UiTheme.SideM;
        UiTheme.GUIBox(new Rect(x, y, w, h), "AR · RESULTADOS OPENSEES");
        float ly = y + 30f, lx = x + 12f, iw = w - 24f;

        // Escala / modo
        GUI.Label(new Rect(lx, ly, iw, 18f), "ESCALA Y UBICACION DEL MODELO", UiTheme.Header); ly += 18f;
        string[] modes = { "1:1 COLUMNA", "MAQUETA 1:100", "SOBRE PLANO" };
        float bw = (iw - 8f) / 3f;
        for (int i = 0; i < 3; i++)
        {
            bool on = (int)structure.mode == i;
            if (GUI.Toggle(new Rect(lx + i * (bw + 4f), ly, bw, 32f), on, modes[i], GUI.skin.button) && !on)
            {
                structure.SetMode((ARStructure.Mode)i);
            }
        }
        ly += 36f;
        GUI.Label(new Rect(lx, ly, iw, 36f),
            $"s = {(structure.Scale >= 0.999f ? "1" : "1/" + (1f / structure.Scale).ToString("0"))} | p_ref = ({structure.RefPoint.x:0.00}, {structure.RefPoint.y:0.00}, {structure.RefPoint.z:0.00}) m",
            UiTheme.DimLabel);
        ly += 22f;

        // Combinacion
        GUI.Label(new Rect(lx, ly, iw, 18f), "CASO / COMBINACION", UiTheme.Header); ly += 18f;
        float cw = (iw - 6f * 3f) / 7f;
        for (int i = 0; i < Combos.Length; i++)
        {
            if (GUI.Toggle(new Rect(lx + i * (cw + 3f), ly, cw, 30f), combo == Combos[i], Combos[i], GUI.skin.button)) combo = Combos[i];
        }
        ly += 32f;
        ComboInfo info = UnityData.GetComboInfo(combo);
        GUI.Label(new Rect(lx, ly, iw, 18f), info != null ? info.label : CaseLabel(combo), UiTheme.DimLabel); ly += 22f;

        // Elemento
        ElementData e = structure.Selected;
        GUI.Label(new Rect(lx, ly, iw, 18f), "ELEMENTO (toca una barra, flechas o acceso directo)", UiTheme.Header); ly += 18f;
        float fw = (iw - 4f * (ARStructure.FeaturedTags.Length - 1)) / ARStructure.FeaturedTags.Length;
        for (int i = 0; i < ARStructure.FeaturedTags.Length; i++)
        {
            string tag = ARStructure.FeaturedTags[i];
            bool on = e != null && e.elementTag == tag;
            if (GUI.Toggle(new Rect(lx + i * (fw + 4f), ly, fw, 30f), on, tag, GUI.skin.button) && !on)
            {
                Select(structure.FindByTag(tag));
                e = structure.Selected;
            }
        }
        ly += 34f;
        if (GUI.Button(new Rect(lx, ly, 44f, 32f), "<")) Step(-1);
        if (GUI.Button(new Rect(lx + iw - 44f, ly, 44f, 32f), ">")) Step(1);
        GUI.Label(new Rect(lx + 52f, ly + 2f, iw - 104f, 30f),
            e != null ? $"{e.elementTag}  ·  {e.type} {e.sectionId}" : "-", UiTheme.TitleSm);
        ly += 36f;
        if (e == null) return;

        Vector3 pi = structure.NodePos(e.nodeI), pj = structure.NodePos(e.nodeJ);
        GUI.Label(new Rect(lx, ly, iw, 18f), $"id {e.id} | I ({pi.x:0.00}, {pi.y:0.00}, {pi.z:0.00})  J ({pj.x:0.00}, {pj.y:0.00}, {pj.z:0.00})", UiTheme.DimLabel);
        ly += 20f;

        // Esfuerzos internos en I, centro y J (ejes locales)
        GUI.Label(new Rect(lx, ly, iw, 18f), "ESFUERZOS INTERNOS (kN, kN·m, ejes locales)", UiTheme.Header); ly += 18f;
        GUI.Label(new Rect(lx, ly, iw, 18f), "      N        Vy       Vz       My       Mz", UiTheme.DimLabel); ly += 17f;
        foreach (var (name, t) in new[] { ("I", 0f), ("½", 0.5f), ("J", 1f) })
        {
            float[] r = UnityData.InternalForcesAt(e, t, combo);
            string row = r == null ? "sin datos"
                : $"{F(r[0])} {F(r[1])} {F(r[2])} {F(r[4])} {F(r[5])}";
            GUI.Label(new Rect(lx, ly, iw, 18f), name + "  " + row, UiTheme.Label);
            ly += 17f;
        }
        // Momento resultante maximo a lo largo de la barra (41 puntos)
        float mMax = 0f, xMax = 0f, len = Vector3.Distance(pi, pj);
        for (int k = 0; k <= 40; k++)
        {
            float[] r = UnityData.InternalForcesAt(e, k / 40f, combo);
            if (r == null) break;
            float m = Mathf.Sqrt(r[4] * r[4] + r[5] * r[5]);
            if (m > mMax) { mMax = m; xMax = len * k / 40f; }
        }
        GUI.Label(new Rect(lx, ly, iw, 18f), $"|M| max a lo largo = {mMax:0.0} kN·m en x = {xMax:0.00} m de I", UiTheme.Label);
        ly += 24f;

        // Desplazamiento del nodo superior / J
        Vector3 uu = UnityData.GetNodeDisplacement(combo, e.nodeJ) * 1000f;   // orden Unity (ux, uz, uy)
        Vector3 u = new Vector3(uu.x, uu.z, uu.y);
        GUI.Label(new Rect(lx, ly, iw, 18f), "DESPLAZAMIENTO NODO J (mm)", UiTheme.Header); ly += 18f;
        GUI.Label(new Rect(lx, ly, iw, 18f), $"ux {u.x:0.00} | uy {u.y:0.00} | uz {u.z:0.00} | |u| {u.magnitude:0.00}", UiTheme.Label);
        ly += 24f;

        // P-M
        GUI.Label(new Rect(lx, ly, iw, 18f), "DEMANDA P-M", UiTheme.Header); ly += 18f;
        Vector2 pm = UnityData.PMDemand(e, combo);
        string pmLine = $"P = {pm.x:0.0} kN (compresion +) | M = {pm.y:0.0} kN·m";
        // misma curva que el viewer: la de DISENO de la seccion + armadura (pmCurveId); la de fibra solo si no hay
        PMCurveData curve = e.type != "columna" ? null
            : (!string.IsNullOrEmpty(e.pmCurveId) ? UnityData.GetPMCurve(e.pmCurveId) : null)
              ?? UnityData.GetPMCurve(e.sectionId + "_FIBER") ?? UnityData.GetPMCurve(e.sectionId);
        GUI.Label(new Rect(lx, ly, iw, 18f), pmLine, UiTheme.Label); ly += 17f;
        if (curve != null && curve.points != null && curve.points.Length >= 2)
        {
            float mCap = CapacityAt(curve, pm.x);
            string ratio = mCap > 1e-3f ? $"{pm.y / mCap:0.00}" : "fuera de la curva";
            GUI.Label(new Rect(lx, ly, iw, 34f),
                $"{curve.sectionId}: phiMn(P) = {mCap:0.0} kN·m -> C = M/phiMn = {ratio} ({curve.points.Length} puntos, interp. lineal)", UiTheme.DimLabel);
            ly += 34f;
        }
        else ly += 4f;

        // Area tributaria (vigas) o carga axial por caso (columnas), del modelo vigente
        UnityData.LocalAxes(e, out _, out _, out _, out float largo);
        if (e.type == "viga")
        {
            GUI.Label(new Rect(lx, ly, iw, 18f), "AREA TRIBUTARIA Y CARGA REPARTIDA", UiTheme.Header); ly += 18f;
            float wG = largo > 0f ? (e.deadLoad + e.selfWeight_kN) / largo : 0f;
            float wQ = largo > 0f ? e.liveLoad / largo : 0f;
            GUI.Label(new Rect(lx, ly, iw, 34f),
                $"A_trib = {e.areaTributaria:0.00} m² | wG = {wG:0.0} kN/m (losa + peso propio) | wQ = {wQ:0.0} kN/m", UiTheme.Label);
        }
        else
        {
            GUI.Label(new Rect(lx, ly, iw, 18f), "CARGA AXIAL POR CASO (base del elemento)", UiTheme.Header); ly += 18f;
            float[] fg = UnityData.InternalForcesAt(e, 0f, "G");
            float[] fq = UnityData.InternalForcesAt(e, 0f, "Q");
            GUI.Label(new Rect(lx, ly, iw, 34f),
                $"N(G) = {(fg != null ? fg[0] : 0f):0.0} kN | N(Q) = {(fq != null ? fq[0] : 0f):0.0} kN | peso propio {e.selfWeight_kN:0.0} kN", UiTheme.Label);
        }
        ly += 36f;

        GUI.Label(new Rect(lx, ly, iw, 52f),
            "Calculado antes en el PC con OpenSees; el telefono solo lee el JSON, interpola esfuerzos y transforma coordenadas.",
            UiTheme.DimLabel);
    }

    private void Step(int dir)
    {
        if (sector.Count == 0) return;
        int i = sector.IndexOf(structure.Selected);
        i = (i + dir + sector.Count) % sector.Count;
        Select(sector[i]);
    }

    private static string F(float v)
    {
        return v.ToString("0.0").PadLeft(8);
    }

    private static string CaseLabel(string c)
    {
        switch (c)
        {
            case "G": return "G: peso propio + sobrecarga muerta";
            case "Q": return "Q: sobrecarga de uso";
            case "EX": return "EX: sismo en X";
            case "EY": return "EY: sismo en Y";
            default: return c;
        }
    }

    /// Momento resistente para una carga axial P interpolando la curva por tramos (puntos ordenados por P).
    private static float CapacityAt(PMCurveData curve, float P)
    {
        var pts = new List<PMPoint>(curve.points);
        pts.Sort((a, b) => a.P_kN.CompareTo(b.P_kN));
        if (P <= pts[0].P_kN || P >= pts[pts.Count - 1].P_kN) return 0f;
        for (int i = 0; i < pts.Count - 1; i++)
        {
            if (P >= pts[i].P_kN && P <= pts[i + 1].P_kN)
            {
                float t = (P - pts[i].P_kN) / Mathf.Max(1e-6f, pts[i + 1].P_kN - pts[i].P_kN);
                return Mathf.Lerp(Mathf.Abs(pts[i].M_kN_m), Mathf.Abs(pts[i + 1].M_kN_m), t);
            }
        }
        return 0f;
    }
}
