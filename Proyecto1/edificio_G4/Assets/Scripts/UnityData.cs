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

    // ---------------------------------------------------------------
    // SIDEQUEST · CARGA MOVIL
    // Combo sintetico "MOV" = Σ coef_k · caso_unitario_k, con coef de las
    // fuerzas de empotramiento de P en la posicion s (ver carga_movil.py).
    // Es exacto (modelo lineal) y continuo en s; P es un factor de escala.
    // ---------------------------------------------------------------
    public const string MovingLoadComboName = "MOV";

    public class MovingLoadState
    {
        public MovingLoadPath path;
        public MovingLoadBeam beam;
        public float s, P, a, b, L;
        public float FA, FB, MA, MB;
        public float sumRz;
        public Vector3 worldPoint;     // punto de aplicacion (coordenadas Unity)
        public int loadedElement;
        public bool loadedFromNodeI;   // true si nodeI del elemento es el nodo A del camino
    }

    public static MovingLoadState MovingLoad;

    public static MovingLoadData GetMovingLoadData()
    {
        return Structure != null && Structure.p1l4 != null ? Structure.p1l4.cargaMovil : null;
    }

    public static MovingLoadState ApplyMovingLoad(MovingLoadPath path, float s, float P)
    {
        MovingLoadData ml = GetMovingLoadData();
        if (ml == null || path == null || path.beams == null || path.beams.Length == 0) return null;

        s = Mathf.Clamp(s, 0f, path.largo);
        MovingLoadBeam beam = path.beams[path.beams.Length - 1];
        foreach (MovingLoadBeam bm in path.beams)
        {
            if (s <= bm.s1 + 1e-6f) { beam = bm; break; }
        }
        float L = beam.s1 - beam.s0;
        float a = Mathf.Clamp(s - beam.s0, 0f, L);
        float b = L - a;
        var st = new MovingLoadState
        {
            path = path, beam = beam, s = s, P = P, a = a, b = b, L = L,
            FA = P * b * b * (3f * a + b) / (L * L * L),
            FB = P * a * a * (a + 3f * b) / (L * L * L),
            MA = P * a * b * b / (L * L),
            MB = -P * a * a * b / (L * L),
            loadedElement = beam.element
        };

        // coeficientes de los 4 casos unitarios involucrados
        var coefs = new List<KeyValuePair<MovingLoadUnitCase, float>>();
        foreach (MovingLoadUnitCase uc in path.unitCases)
        {
            float c = 0f;
            if (uc.node == beam.nodeA) c = uc.tipo == "F" ? st.FA : st.MA;
            else if (uc.node == beam.nodeB) c = uc.tipo == "F" ? st.FB : st.MB;
            if (Mathf.Abs(c) > 1e-9f) coefs.Add(new KeyValuePair<MovingLoadUnitCase, float>(uc, c));
        }

        // desplazamientos (solo el edificio cargado responde: junta de dilatacion)
        var disp = new List<DisplacementRecord>(path.nodeIds.Length);
        for (int i = 0; i < path.nodeIds.Length; i++)
        {
            float ux = 0f, uy = 0f, uz = 0f;
            foreach (var kv in coefs)
            {
                ux += kv.Value * kv.Key.disp[3 * i];
                uy += kv.Value * kv.Key.disp[3 * i + 1];
                uz += kv.Value * kv.Key.disp[3 * i + 2];
            }
            disp.Add(new DisplacementRecord { combo = MovingLoadComboName, node = path.nodeIds[i], ux = ux, uy = uy, uz = uz });
        }

        // fuerzas internas (+ fuerzas de empotramiento en la viga cargada);
        // los elementos del otro edificio quedan con fuerzas nulas
        float dx = path.dir[0], dy = path.dir[1];
        Vector3 axis = new Vector3(-dy, dx, 0f);   // z x dir en coordenadas del modelo
        var index = new Dictionary<int, int>(path.elementIds.Length);
        for (int e = 0; e < path.elementIds.Length; e++) index[path.elementIds[e]] = e;
        var forces = new List<ElementForceRecord>();
        foreach (ElementData ed in Structure.elements)
        {
            float[] f = new float[12];
            if (ed != null && index.TryGetValue(ed.id, out int e))
            {
                foreach (var kv in coefs)
                {
                    for (int k = 0; k < 12; k++) f[k] += kv.Value * kv.Key.forces[12 * e + k];
                }
            }
            if (ed != null && ed.id == beam.element)
            {
                st.loadedFromNodeI = ed.nodeI == beam.nodeA;
                int iA = st.loadedFromNodeI ? 0 : 6;
                int iB = st.loadedFromNodeI ? 6 : 0;
                // reacciones de empotramiento (fuerzas sobre el elemento), proyectadas a ejes locales
                AddLocal(f, iA, ed, new Vector3(0f, 0f, st.FA), -st.MA * axis);
                AddLocal(f, iB, ed, new Vector3(0f, 0f, st.FB), -st.MB * axis);
            }
            if (ed != null) forces.Add(new ElementForceRecord { combo = MovingLoadComboName, id = ed.id, f = f });
        }

        foreach (var kv in coefs) st.sumRz += kv.Value * kv.Key.sumRz;

        float gx = path.origen.x + dx * s;
        float gy = path.origen.y + dy * s;
        st.worldPoint = new Vector3(gx, path.z, gy);

        if (DisplacementsByCombo == null) DisplacementsByCombo = new Dictionary<string, List<DisplacementRecord>>();
        if (ElementForcesByCombo == null) ElementForcesByCombo = new Dictionary<string, List<ElementForceRecord>>();
        DisplacementsByCombo[MovingLoadComboName] = disp;
        ElementForcesByCombo[MovingLoadComboName] = forces;
        if (comboLookup == null) comboLookup = new Dictionary<string, ComboInfo>();
        comboLookup[MovingLoadComboName] = new ComboInfo
        {
            name = MovingLoadComboName,
            label = $"Carga movil P={P:0.#} kN en s={s:0.00} m ({path.nombre})"
        };
        MovingLoad = st;
        ActiveCombo = MovingLoadComboName;
        return st;
    }


    // ---------------------------------------------------------------
    // CARGA EN ELEMENTO (puntual o distribuida, elegida por id/tag)
    // Combo sintetico "PUN" = Σ q_k · caso_unitario_k, con q_k las fuerzas
    // de empotramiento perfecto de la carga en los 12 GDL de los nodos del
    // elemento (carga_elemento.py precalcula los 12 casos unitarios).
    // ---------------------------------------------------------------
    public const string ElementLoadComboName = "PUN";

    public class ElementLoadState
    {
        public ElementLoadCases cases;
        public bool distributed;
        public Vector3 dir;          // direccion de la carga (unitaria, ejes del modelo)
        public float P, a;           // puntual
        public float w, x1, x2;      // distribuida en [x1, x2]
        public float L;
        public Vector3 total;        // resultante aplicada [kN]
        public Vector3 sumR;         // suma de reacciones [kN]
        public float[] qI = new float[6], qJ = new float[6];   // fuerzas equivalentes en I y J
        public Vector3 pI, pJ;       // coordenadas del modelo de los nodos
        public float transversal;    // fraccion transversal de la direccion (|t|)
        public Vector3 dirLocal;     // parte de la carga que flecta el elemento (en vigas de piso: solo la vertical)
        public float[] qILocal = new float[6], qJLocal = new float[6];   // empotramiento de dirLocal
    }

    public static ElementLoadState ElementLoad;

    public static Vector3 NodeModel(int id)
    {
        if (Structure != null && Structure.nodes != null)
        {
            foreach (NodeData n in Structure.nodes)
            {
                if (n.id == id) return new Vector3(n.x, n.y, n.z);
            }
        }
        return Vector3.zero;
    }

    /// Suma a qI/qJ las fuerzas de empotramiento de una carga puntual P (dir) en a.
    private static void AddPointFixedEnd(float[] qI, float[] qJ, Vector3 d, Vector3 u, float L, float a, float P)
    {
        float b = L - a;
        float pa = P * Vector3.Dot(u, d);
        Vector3 t = u - Vector3.Dot(u, d) * d;
        float tn = t.magnitude;
        float pt = P * tn;
        t = tn > 1e-6f ? t / tn : Vector3.zero;
        Vector3 ax = Vector3.Cross(d, t);
        Vector3 fi = pa * b / L * d + pt * b * b * (3f * a + b) / (L * L * L) * t;
        Vector3 fj = pa * a / L * d + pt * a * a * (a + 3f * b) / (L * L * L) * t;
        Vector3 mi = pt * a * b * b / (L * L) * ax;
        Vector3 mj = -pt * a * a * b / (L * L) * ax;
        for (int k = 0; k < 3; k++)
        {
            qI[k] += fi[k]; qI[k + 3] += mi[k];
            qJ[k] += fj[k]; qJ[k + 3] += mj[k];
        }
    }

    /// Carga puntual P en a: empotramiento de la parte local + reparto estatico de la parte al diafragma.
    private static void AddPointLoad(ElementLoadState st, Vector3 d, float a, float P, Vector3 dirDiaphragm)
    {
        AddPointFixedEnd(st.qILocal, st.qJLocal, d, st.dirLocal, st.L, a, P);
        AddPointFixedEnd(st.qI, st.qJ, d, st.dirLocal, st.L, a, P);
        float b = st.L - a;
        for (int k = 0; k < 3; k++)
        {
            st.qI[k] += P * b / st.L * dirDiaphragm[k];
            st.qJ[k] += P * a / st.L * dirDiaphragm[k];
        }
    }

    private const int DistSteps = 48;   // Simpson (par) para la carga distribuida

    public static ElementLoadState ApplyElementLoad(ElementLoadCases cases, bool distributed, Vector3 dir,
        float P, float a, float w, float x1, float x2)
    {
        if (cases == null || cases.unitCases == null || cases.unitCases.Length < 12) return null;
        var st = new ElementLoadState
        {
            cases = cases, distributed = distributed, dir = dir.normalized, P = P, a = a, w = w,
            x1 = Mathf.Min(x1, x2), x2 = Mathf.Max(x1, x2)
        };
        st.pI = NodeModel(cases.nodeI);
        st.pJ = NodeModel(cases.nodeJ);
        Vector3 d = st.pJ - st.pI;
        st.L = d.magnitude;
        d /= st.L;
        st.transversal = (st.dir - Vector3.Dot(st.dir, d) * d).magnitude;

        // Viga de piso (horizontal, en el diafragma rigido): la componente horizontal
        // de la carga la toma la losa (diafragma) y se reparte estaticamente a los
        // nodos, sin flexion local en planta; solo la vertical flecta la viga.
        bool floorBeam = Mathf.Abs(d.z) < 1e-4f;
        st.dirLocal = floorBeam ? new Vector3(0f, 0f, st.dir.z) : st.dir;
        Vector3 dirDiaphragm = st.dir - st.dirLocal;

        if (!distributed)
        {
            st.a = Mathf.Clamp(a, 0f, st.L);
            AddPointLoad(st, d, st.a, P, dirDiaphragm);
            st.total = P * st.dir;
        }
        else
        {
            float span = st.x2 - st.x1;
            if (span > 1e-6f)
            {
                float h = span / DistSteps;
                for (int k = 0; k <= DistSteps; k++)
                {
                    float wk = (k == 0 || k == DistSteps) ? 1f : (k % 2 == 1 ? 4f : 2f);
                    AddPointLoad(st, d, st.x1 + k * h, w * wk * h / 3f, dirDiaphragm);
                }
            }
            st.total = w * span * st.dir;
        }

        // coeficientes de los 12 casos unitarios
        float[] coef = new float[cases.unitCases.Length];
        for (int c = 0; c < cases.unitCases.Length; c++)
        {
            ElementLoadUnitCase uc = cases.unitCases[c];
            coef[c] = uc.node == cases.nodeI ? st.qI[uc.dof] : st.qJ[uc.dof];
        }

        var disp = new List<DisplacementRecord>(cases.nodeIds.Length);
        for (int i = 0; i < cases.nodeIds.Length; i++)
        {
            float ux = 0f, uy = 0f, uz = 0f;
            for (int c = 0; c < coef.Length; c++)
            {
                if (Mathf.Abs(coef[c]) < 1e-12f) continue;
                float[] dv = cases.unitCases[c].disp;
                ux += coef[c] * dv[3 * i];
                uy += coef[c] * dv[3 * i + 1];
                uz += coef[c] * dv[3 * i + 2];
            }
            disp.Add(new DisplacementRecord { combo = ElementLoadComboName, node = cases.nodeIds[i], ux = ux, uy = uy, uz = uz });
        }

        var index = new Dictionary<int, int>(cases.elementIds.Length);
        for (int e = 0; e < cases.elementIds.Length; e++) index[cases.elementIds[e]] = e;
        var forces = new List<ElementForceRecord>();
        foreach (ElementData ed in Structure.elements)
        {
            if (ed == null) continue;
            float[] f = new float[12];
            if (index.TryGetValue(ed.id, out int e))
            {
                for (int c = 0; c < coef.Length; c++)
                {
                    if (Mathf.Abs(coef[c]) < 1e-12f) continue;
                    float[] fv = cases.unitCases[c].forces;
                    for (int k = 0; k < 12; k++) f[k] += coef[c] * fv[12 * e + k];
                }
            }
            if (ed.id == cases.element)
            {
                // fuerzas de extremo reales = K·u + reacciones de empotramiento (= -cargas equivalentes)
                // solo la parte que flecta el elemento tiene reacciones de empotramiento
                AddLocal(f, 0, ed, -new Vector3(st.qILocal[0], st.qILocal[1], st.qILocal[2]), -new Vector3(st.qILocal[3], st.qILocal[4], st.qILocal[5]));
                AddLocal(f, 6, ed, -new Vector3(st.qJLocal[0], st.qJLocal[1], st.qJLocal[2]), -new Vector3(st.qJLocal[3], st.qJLocal[4], st.qJLocal[5]));
            }
            forces.Add(new ElementForceRecord { combo = ElementLoadComboName, id = ed.id, f = f });
        }

        for (int c = 0; c < coef.Length; c++)
        {
            float[] r = cases.unitCases[c].sumR;
            st.sumR += coef[c] * new Vector3(r[0], r[1], r[2]);
        }

        if (DisplacementsByCombo == null) DisplacementsByCombo = new Dictionary<string, List<DisplacementRecord>>();
        if (ElementForcesByCombo == null) ElementForcesByCombo = new Dictionary<string, List<ElementForceRecord>>();
        DisplacementsByCombo[ElementLoadComboName] = disp;
        ElementForcesByCombo[ElementLoadComboName] = forces;
        if (comboLookup == null) comboLookup = new Dictionary<string, ComboInfo>();
        comboLookup[ElementLoadComboName] = new ComboInfo
        {
            name = ElementLoadComboName,
            label = distributed
                ? $"Carga distribuida w={w:0.##} kN/m en {cases.tag} [{st.x1:0.00}, {st.x2:0.00}] m"
                : $"Carga puntual P={P:0.##} kN en {cases.tag} a={st.a:0.00} m"
        };
        ElementLoad = st;
        ActiveCombo = ElementLoadComboName;
        return st;
    }


    // ---------------------------------------------------------------
    // QUITAR ELEMENTO: reemplaza en memoria los resultados de los casos
    // base y combos por los del reanalisis (quitar_elemento.py) y guarda
    // los originales para restaurar. No toca ningun archivo.
    // ---------------------------------------------------------------
    public static readonly string[] AnalysisCombos = { "G", "Q", "EX", "EY", "C1", "C2", "C3" };
    public static HashSet<int> RemovedElements = new HashSet<int>();
    public static ElementRemovalResult Removal;
    private static Dictionary<string, List<DisplacementRecord>> originalDisp;
    private static Dictionary<string, List<ElementForceRecord>> originalForces;

    public static bool IsModelModified => RemovedElements != null && RemovedElements.Count > 0;

    // Deformada: comparar original (naranjo) vs modificada (verde) y escala fija opcional
    public static bool CompareDeformed = true;
    public static bool CompareDeformedActive => CompareDeformed && IsModelModified && originalDisp != null
        && System.Array.IndexOf(AnalysisCombos, ActiveCombo) >= 0;
    public static float DeformedScaleOverride = 0f;   // 0 = automatica por edificio

    public static bool IsRemoved(int elementId)
    {
        return RemovedElements != null && RemovedElements.Contains(elementId);
    }

    public static void ApplyRemovalResults(ElementRemovalResult result)
    {
        if (result == null) return;
        if (originalDisp == null)
        {
            originalDisp = new Dictionary<string, List<DisplacementRecord>>();
            originalForces = new Dictionary<string, List<ElementForceRecord>>();
            foreach (string c in AnalysisCombos)
            {
                if (DisplacementsByCombo != null && DisplacementsByCombo.TryGetValue(c, out var d)) originalDisp[c] = d;
                if (ElementForcesByCombo != null && ElementForcesByCombo.TryGetValue(c, out var f)) originalForces[c] = f;
            }
        }
        var disp = new Dictionary<string, List<DisplacementRecord>>();
        foreach (DisplacementRecord d in result.displacements)
        {
            if (!disp.TryGetValue(d.combo, out var list)) disp[d.combo] = list = new List<DisplacementRecord>();
            list.Add(d);
        }
        var forces = new Dictionary<string, List<ElementForceRecord>>();
        foreach (ElementForceRecord f in result.elementForces)
        {
            if (!forces.TryGetValue(f.combo, out var list)) forces[f.combo] = list = new List<ElementForceRecord>();
            list.Add(f);
        }
        foreach (string c in AnalysisCombos)
        {
            if (disp.TryGetValue(c, out var d)) DisplacementsByCombo[c] = d;
            if (forces.TryGetValue(c, out var f)) ElementForcesByCombo[c] = f;
        }
        RemovedElements = new HashSet<int>();
        foreach (RemovedElementInfo r in result.removed) RemovedElements.Add(r.id);
        Removal = result;
    }

    public static void RestoreOriginalModel()
    {
        if (originalDisp != null)
        {
            foreach (var kv in originalDisp) DisplacementsByCombo[kv.Key] = kv.Value;
            foreach (var kv in originalForces) ElementForcesByCombo[kv.Key] = kv.Value;
        }
        originalDisp = null;
        originalForces = null;
        RemovedElements = new HashSet<int>();
        Removal = null;
    }

    /// Olvida el estado de reanalisis sin restaurar (al recargar la estructura).
    public static void ResetRemovalState()
    {
        originalDisp = null;
        originalForces = null;
        RemovedElements = new HashSet<int>();
        Removal = null;
    }

    /// Resultados originales (para comparar antes/despues en el panel).
    public static float[] GetOriginalElementForces(string combo, int elementId)
    {
        if (originalForces == null || !originalForces.TryGetValue(combo, out var list)) return GetElementForces(combo, elementId);
        foreach (ElementForceRecord f in list) if (f != null && f.id == elementId) return f.f;
        return null;
    }

    public static Vector3 GetOriginalNodeDisplacement(string combo, int nodeId)
    {
        if (originalDisp == null || !originalDisp.TryGetValue(combo, out var list)) return GetNodeDisplacement(combo, nodeId);
        foreach (DisplacementRecord d in list) if (d.node == nodeId) return new Vector3(d.ux, d.uz, d.uy);
        return Vector3.zero;
    }

    // ---------------------------------------------------------------
    // ESFUERZOS INTERNOS EN EJES LOCALES
    // Las fuerzas del JSON son fuerzas de extremo en ejes locales del
    // elemento (OpenSees localForce): [N, Vy, Vz, T, My, Mz] en I y en J.
    // Esfuerzo interno en x = t*L: lerp(-F_I, +F_J, t) + efecto de las
    // cargas dentro del tramo (gravedad repartida del combo, carga movil o
    // carga en elemento), que el analisis aplica como cargas nodales.
    // ---------------------------------------------------------------

    /// Ejes locales del elemento igual que geomTransf de carga_viva_sismo.py
    /// (vecxz = X si el elemento es casi vertical, Z en otro caso).
    public static void LocalAxes(ElementData e, out Vector3 x, out Vector3 y, out Vector3 z, out float length)
    {
        Vector3 d = NodeModel(e.nodeJ) - NodeModel(e.nodeI);
        length = d.magnitude;
        x = length > 1e-9f ? d / length : Vector3.right;
        Vector3 vecxz = length > 0f && Mathf.Abs(d.z) / length > 0.90f ? Vector3.right : Vector3.forward;
        // Vector3.forward = (0,0,1): eje Z del modelo (coordenadas del modelo, no de Unity)
        y = Vector3.Cross(vecxz, x).normalized;
        z = Vector3.Cross(x, y);
    }

    /// Suma a f (en el extremo base 0 o 6) una fuerza y un momento globales proyectados a ejes locales.
    private static void AddLocal(float[] f, int baseIndex, ElementData e, Vector3 force, Vector3 moment)
    {
        LocalAxes(e, out Vector3 x, out Vector3 y, out Vector3 z, out _);
        f[baseIndex + 0] += Vector3.Dot(force, x);
        f[baseIndex + 1] += Vector3.Dot(force, y);
        f[baseIndex + 2] += Vector3.Dot(force, z);
        f[baseIndex + 3] += Vector3.Dot(moment, x);
        f[baseIndex + 4] += Vector3.Dot(moment, y);
        f[baseIndex + 5] += Vector3.Dot(moment, z);
    }

    /// Factores (lambda_G, lambda_Q) del caso o combo para la carga gravitacional repartida.
    private static void GravityLambdas(string combo, out float lg, out float lq)
    {
        lg = lq = 0f;
        if (combo == "G") { lg = 1f; return; }
        if (combo == "Q") { lq = 1f; return; }
        ComboInfo info = GetComboInfo(combo);
        if (info != null && combo != MovingLoadComboName && combo != ElementLoadComboName)
        {
            lg = info.G;
            lq = info.Q;
        }
    }

    // Viga simplemente apoyada (largo L) con carga transversal: corte S(x) y momento M(x).
    // Puntual P en a, o repartida w en [x1, x2].
    private static void SimpleSpan(float L, float x, bool distributed, float P, float a, float w, float x1, float x2,
        out float S, out float M)
    {
        if (!distributed)
        {
            float b = L - a;
            float ri = P * b / L;
            S = x < a ? ri : ri - P;
            M = x <= a ? ri * x : ri * x - P * (x - a);
            return;
        }
        float s = Mathf.Max(0f, x2 - x1);
        float W = w * s;
        float xc = x1 + 0.5f * s;
        float riD = W * (L - xc) / L;
        float c = Mathf.Clamp(x, x1, x2) - x1;          // largo cargado a la izquierda de x
        S = riD - w * c;
        M = riD * x - w * c * (x - (x1 + 0.5f * c));
    }

    private struct SpanLoad
    {
        public Vector3 dir;        // direccion unitaria de la carga (modelo)
        public bool distributed;
        public float P, a, w, x1, x2;
        public bool deviationOnly; // true: los extremos ya incluyen las reacciones de empotramiento
    }

    private static List<SpanLoad> SpanLoadsFor(ElementData e, string combo, float L)
    {
        var loads = new List<SpanLoad>();
        if (combo == MovingLoadComboName)
        {
            MovingLoadState st = MovingLoad;
            if (st != null && st.loadedElement == e.id)
            {
                float aE = st.loadedFromNodeI ? st.a : st.L - st.a;
                loads.Add(new SpanLoad { dir = new Vector3(0f, 0f, -1f), P = st.P, a = aE, deviationOnly = true });
            }
            return loads;
        }
        if (combo == ElementLoadComboName)
        {
            ElementLoadState st = ElementLoad;
            if (st != null && st.cases != null && st.cases.element == e.id)
            {
                loads.Add(new SpanLoad
                {
                    dir = st.dirLocal, distributed = st.distributed, P = st.P, a = st.a, w = st.w, x1 = st.x1, x2 = st.x2,
                    deviationOnly = true
                });
            }
            return loads;
        }
        if (L > 1e-6f)
        {
            // G y Q se analizan como carga repartida (eleLoad): las fuerzas de extremo
            // ya traen las reacciones y el empotramiento; solo falta la curvatura del
            // momento dentro del tramo (deviationOnly).
            GravityLambdas(combo, out float lg, out float lq);
            float slab = e.type == "viga" ? lg * e.deadLoad + lq * e.liveLoad : 0f;
            float total = slab + lg * e.selfWeight_kN;   // kN totales del tramo
            if (Mathf.Abs(total) > 1e-9f)
            {
                loads.Add(new SpanLoad { dir = new Vector3(0f, 0f, -1f), distributed = true, w = total / L, x1 = 0f, x2 = L, deviationOnly = true });
            }
        }
        return loads;
    }

    /// Esfuerzos internos [N, Vy, Vz, T, My, Mz] (ejes locales) en t = x/L para el combo activo.
    /// Devuelve null si el combo no tiene fuerzas para el elemento.
    public static float[] InternalForcesAt(ElementData e, float t, string combo = null)
    {
        combo = combo ?? ActiveCombo;
        float[] f = GetElementForces(combo, e.id);
        if (f == null || f.Length < 12) return null;
        t = Mathf.Clamp01(t);
        float[] r = new float[6];
        for (int k = 0; k < 6; k++) r[k] = Mathf.Lerp(-f[k], f[k + 6], t);

        LocalAxes(e, out Vector3 lx, out Vector3 ly, out Vector3 lz, out float L);
        float x = t * L;
        foreach (SpanLoad load in SpanLoadsFor(e, combo, L))
        {
            // componente axial (a lo largo de lx) y transversal (direccion tt)
            float axialFrac = Vector3.Dot(load.dir, lx);
            Vector3 tv = load.dir - axialFrac * lx;
            float transFrac = tv.magnitude;
            Vector3 tt = transFrac > 1e-6f ? tv / transFrac : Vector3.zero;

            SimpleSpan(L, x, load.distributed, load.P, load.a, load.w, load.x1, load.x2, out float S, out float M);
            float S0 = 0f, SL = 0f;
            if (load.deviationOnly)
            {
                SimpleSpan(L, 0f, load.distributed, load.P, load.a, load.w, load.x1, load.x2, out S0, out _);
                SimpleSpan(L, L, load.distributed, load.P, load.a, load.w, load.x1, load.x2, out SL, out _);
            }
            float dev = load.deviationOnly ? Mathf.Lerp(S0, SL, t) : 0f;
            // N interno (traccion +) de la componente axial, misma forma que el corte
            r[0] += axialFrac * (S - dev);
            // corte interno = S * tt ; momento interno = -M * (lx x tt)
            Vector3 v = transFrac * (S - dev) * tt;
            Vector3 m = -transFrac * M * Vector3.Cross(lx, tt);
            r[1] += Vector3.Dot(v, ly);
            r[2] += Vector3.Dot(v, lz);
            r[4] += Vector3.Dot(m, ly);
            r[5] += Vector3.Dot(m, lz);
        }
        return r;
    }

    /// Demanda P-M de un elemento: P = compresion (+), M = max |M| resultante en I, centro y J.
    public static Vector2 PMDemand(ElementData e, string combo = null)
    {
        float pComp = 0f, mMax = 0f;
        bool any = false;
        foreach (float t in new[] { 0f, 0.5f, 1f })
        {
            float[] r = InternalForcesAt(e, t, combo);
            if (r == null) continue;
            any = true;
            if (t == 0.5f) pComp = -r[0];
            mMax = Mathf.Max(mMax, Mathf.Sqrt(r[4] * r[4] + r[5] * r[5]));
        }
        return any ? new Vector2(pComp, mMax) : Vector2.zero;
    }

    public static ComboInfo GetComboInfo(string combo)
    {
        if (string.IsNullOrEmpty(combo) || comboLookup == null) return null;
        return comboLookup.TryGetValue(combo, out var info) ? info : null;
    }
}
