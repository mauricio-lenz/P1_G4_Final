using System;
using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Modo "Fachada": recreacion VISUAL del edificio real (fotos del edificio de Ingenieria) sobre el
/// modelo, con su entorno. No toca el analisis ni los datos: solo agrega objetos sin colisionador
/// (no interfieren con la seleccion) y se quita sin dejar rastro.
///   - cerramiento de cada piso: losa de piso y losa de cielo del modelo (interseccion); lo que solo
///     tiene losa de cielo es alero o voladizo abierto. Los huecos interiores no llevan fachada.
///   - cara sur (-y, la de los voladizos): muro cortina de vidrio; norte y laterales: pano naranjo con
///     ventanas y aletas verticales; banda en el borde de cada losa
///   - escaleras segun los planos 2017_67-500 a 503 (graderias, escaleras exteriores del eje 3,
///     escalera norte entre muros y escalera interior del nucleo)
///   - techo con antepecho y equipos; entorno con pasto, plaza, arboles y cielo
/// Coordenadas: modelo (x, y, z arriba) -> Unity (x, z, y).
/// </summary>
public class FacadeView : MonoBehaviour
{
    public static bool Active => instance != null;
    private static FacadeView instance;

    private StructureViewer viewer;
    private readonly List<GameObject> hiddenEnv = new List<GameObject>();
    private Color prevBg, prevAmbient;
    private CameraClearFlags prevFlags;
    private float nextCheck;

    // colores tomados de las fotos
    private static readonly Color Orange = new Color(0.90f, 0.43f, 0.18f);
    private static readonly Color OrangeDark = new Color(0.80f, 0.37f, 0.15f);
    private static readonly Color Concrete = new Color(0.80f, 0.80f, 0.78f);
    private static readonly Color White = new Color(0.93f, 0.93f, 0.90f);
    private static readonly Color Mullion = new Color(0.20f, 0.23f, 0.27f);
    private static readonly Color GlassTint = new Color(0.42f, 0.62f, 0.80f, 0.38f);
    private static readonly Color WindowTint = new Color(0.72f, 0.82f, 0.92f, 1f);
    private static readonly Color Sky = new Color(0.62f, 0.78f, 0.93f);

    private const float MainSouthY = -7.25f;   // eje 3: linea sur de columnas de los dos edificios
    private const float FloorH = 3.96f;

    // planos 2017_67-501: banda de las escaleras exteriores del eje 3 (37 cm fuera del eje, 2,27 m de ancho)
    private const float StairY0 = -7.62f, StairY1 = -9.89f;
    // zonas sin cerramiento por donde pasa una escalera exterior: (x0, x1, y0, y1, nivel de piso del tramo)
    private static readonly (float x0, float x1, float y0, float y1, float z)[] OpenZones =
    {
        (18.5f, 28.7f, -12f, -7.40f, 3.96f),   // escalera piso 1 -> 2 (H, 501 corte A)
        (-0.1f, 11.1f, -12f, -7.40f, 7.92f),   // escalera piso 2 -> 3 (F-G, 501 corte B): sobre el voladizo
    };

    private readonly Dictionary<string, Material> mats = new Dictionary<string, Material>();

    public static void Toggle(StructureViewer viewer)
    {
        if (instance != null) Hide(); else Show(viewer);
    }

    public static void Show(StructureViewer viewer)
    {
        if (instance != null || viewer == null || UnityData.Structure == null) return;
        var go = new GameObject("FacadeView");
        go.hideFlags = HideFlags.DontSave;
        instance = go.AddComponent<FacadeView>();
        instance.viewer = viewer;
        instance.Build();
    }

    public static void Hide()
    {
        if (instance == null) return;
        instance.Restore();
        Destroy(instance.gameObject);
        instance = null;
    }

    private void LateUpdate()
    {
        // si el viewer se reconstruye (reanalisis), el entorno oscuro vuelve a aparecer: se oculta de nuevo
        if (Time.unscaledTime < nextCheck) return;
        nextCheck = Time.unscaledTime + 1f;
        HideEnvironment();
    }

    // ------------------------------------------------------------------
    private void Build()
    {
        Camera cam = Camera.main;
        if (cam != null)
        {
            prevBg = cam.backgroundColor;
            prevFlags = cam.clearFlags;
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = Sky;
        }
        prevAmbient = RenderSettings.ambientLight;
        RenderSettings.ambientLight = new Color(0.58f, 0.60f, 0.64f);
        HideEnvironment();

        List<float> levels = Levels();
        float top = levels.Count > 0 ? levels[levels.Count - 1] : 0f;
        float prev = 0f;
        foreach (float z in levels)
        {
            foreach (Edge e in StoryOutline(prev, z))
            {
                if (e.Length < 0.25f) continue;
                if (IsGlass(e)) GlassStory(e, prev, z); else OrangeStory(e, prev, z);
            }
            foreach (Edge e in SlabOutline(z))
            {
                if (e.Length < 0.25f) continue;
                SlabBand(e, z, IsGlass(e));
                if (Mathf.Approximately(z, top)) Parapet(e, z);
            }
            prev = z;
        }
        Roof(top);
        RoofEquipment(top);
        Ground();
        Plaza();
        Graderias();
        ExteriorStairs();
        NorthStair();
        CoreStair();
        Trees();
    }

    private static bool IsGlass(Edge e)
    {
        bool south = e.normal == Vector2.down;
        bool sideOfSouthVolume = Mathf.Abs(e.normal.x) > 0.9f && 0.5f * (e.a.y + e.b.y) < MainSouthY - 0.2f;
        return south || sideOfSouthVolume;
    }

    private void Restore()
    {
        Camera cam = Camera.main;
        if (cam != null)
        {
            cam.clearFlags = prevFlags;
            cam.backgroundColor = prevBg;
        }
        RenderSettings.ambientLight = prevAmbient;
        foreach (GameObject g in hiddenEnv) if (g != null) g.SetActive(true);
        hiddenEnv.Clear();
    }

    private void HideEnvironment()
    {
        if (viewer == null) return;
        foreach (Transform t in viewer.transform)
        {
            if (t.name.StartsWith("Env_") && t.gameObject.activeSelf)
            {
                t.gameObject.SetActive(false);
                hiddenEnv.Add(t.gameObject);
            }
        }
    }

    // ------------------------------------------------------------------
    // Contornos
    // ------------------------------------------------------------------
    private struct Edge
    {
        public Vector2 a, b, normal;   // modelo (x, y); normal hacia afuera
        public float Length => Vector2.Distance(a, b);
        public Vector2 Dir => (b - a).normalized;
        public Vector2 At(float s) => Vector2.Lerp(a, b, s);
    }

    private static List<float> Levels()
    {
        var set = new SortedSet<float>();
        foreach (SlabData s in UnityData.Structure.slabs)
        {
            float z = Mathf.Round(s.z * 100f) / 100f;
            if (z > 0.01f) set.Add(z);
        }
        return new List<float>(set);
    }

    private static List<Rect> SlabRects(float z)
    {
        var rects = new List<Rect>();
        foreach (SlabData s in UnityData.Structure.slabs)
            if (Mathf.Abs(Mathf.Round(s.z * 100f) / 100f - z) < 0.02f)
                rects.Add(Rect.MinMaxRect(Mathf.Min(s.x0, s.x1), Mathf.Min(s.y0, s.y1), Mathf.Max(s.x0, s.x1), Mathf.Max(s.y0, s.y1)));
        return rects;
    }

    private static bool InAny(List<Rect> rects, Vector2 p)
    {
        foreach (Rect r in rects) if (r.Contains(p)) return true;
        return false;
    }

    /// Contorno exterior de la losa del nivel z (bandas de borde, antepechos, techo).
    private static List<Edge> SlabOutline(float z)
    {
        var rects = SlabRects(z);
        return CellOutline(rects, p => InAny(rects, p));
    }

    /// Cerramiento del piso entre z0 y z1: donde hay losa de piso y de cielo. El primer piso no tiene
    /// losa de piso en el modelo (salvo el subterraneo): se cierra en el cuerpo principal (y >= eje 3),
    /// asi el voladizo queda abierto por debajo. Las zonas de escaleras exteriores quedan afuera.
    private static List<Edge> StoryOutline(float z0, float z1)
    {
        var ceil = SlabRects(z1);
        var floor = z0 > 0.01f ? SlabRects(z0) : null;
        var all = new List<Rect>(ceil);
        if (floor != null) all.AddRange(floor);
        foreach (var o in OpenZones) all.Add(Rect.MinMaxRect(o.x0, o.y0, o.x1, o.y1));
        return CellOutline(all, p =>
        {
            if (!InAny(ceil, p)) return false;
            if (floor != null ? !InAny(floor, p) : p.y < MainSouthY - 0.05f) return false;
            foreach (var o in OpenZones)
                if (Mathf.Abs(o.z - z0) < 0.05f && p.x > o.x0 && p.x < o.x1 && p.y > o.y0 && p.y < o.y1) return false;
            return true;
        });
    }

    /// Bordes entre celdas cubiertas y el exterior, en la grilla formada por los bordes de los rectangulos.
    private static List<Edge> CellOutline(List<Rect> rects, Func<Vector2, bool> covers)
    {
        var xs = Breaks(rects, true);
        var ys = Breaks(rects, false);
        int nx = xs.Count - 1, ny = ys.Count - 1;
        var edges = new List<Edge>();
        if (nx < 1 || ny < 1) return edges;
        var covered = new bool[nx, ny];
        for (int i = 0; i < nx; i++)
            for (int j = 0; j < ny; j++)
                covered[i, j] = covers(new Vector2(0.5f * (xs[i] + xs[i + 1]), 0.5f * (ys[j] + ys[j + 1])));
        // celdas vacias conectadas con el exterior (los huecos interiores no llevan fachada)
        var outside = new bool[nx, ny];
        var stack = new Stack<Vector2Int>();
        for (int i = 0; i < nx; i++) { stack.Push(new Vector2Int(i, 0)); stack.Push(new Vector2Int(i, ny - 1)); }
        for (int j = 0; j < ny; j++) { stack.Push(new Vector2Int(0, j)); stack.Push(new Vector2Int(nx - 1, j)); }
        while (stack.Count > 0)
        {
            var p = stack.Pop();
            if (p.x < 0 || p.y < 0 || p.x >= nx || p.y >= ny || covered[p.x, p.y] || outside[p.x, p.y]) continue;
            outside[p.x, p.y] = true;
            stack.Push(new Vector2Int(p.x + 1, p.y)); stack.Push(new Vector2Int(p.x - 1, p.y));
            stack.Push(new Vector2Int(p.x, p.y + 1)); stack.Push(new Vector2Int(p.x, p.y - 1));
        }
        bool Out(int i, int j) => i < 0 || j < 0 || i >= nx || j >= ny || outside[i, j];
        for (int j = 0; j <= ny; j++)
            for (int side = 0; side < 2; side++)   // 0: hacia -y; 1: hacia +y
            {
                int start = -1;
                for (int i = 0; i <= nx; i++)
                {
                    bool on = i < nx && (side == 0 ? j < ny && covered[i, j] && Out(i, j - 1) : j > 0 && covered[i, j - 1] && Out(i, j));
                    if (on && start < 0) start = i;
                    if (!on && start >= 0)
                    {
                        edges.Add(new Edge { a = new Vector2(xs[start], ys[j]), b = new Vector2(xs[i], ys[j]), normal = side == 0 ? Vector2.down : Vector2.up });
                        start = -1;
                    }
                }
            }
        for (int i = 0; i <= nx; i++)
            for (int side = 0; side < 2; side++)   // 0: hacia -x; 1: hacia +x
            {
                int start = -1;
                for (int j = 0; j <= ny; j++)
                {
                    bool on = j < ny && (side == 0 ? i < nx && covered[i, j] && Out(i - 1, j) : i > 0 && covered[i - 1, j] && Out(i, j));
                    if (on && start < 0) start = j;
                    if (!on && start >= 0)
                    {
                        edges.Add(new Edge { a = new Vector2(xs[i], ys[start]), b = new Vector2(xs[i], ys[j]), normal = side == 0 ? Vector2.left : Vector2.right });
                        start = -1;
                    }
                }
            }
        return edges;
    }

    private static List<float> Breaks(List<Rect> rects, bool x)
    {
        var set = new SortedSet<float>();
        foreach (Rect r in rects)
        {
            set.Add(Mathf.Round((x ? r.xMin : r.yMin) * 100f) / 100f);
            set.Add(Mathf.Round((x ? r.xMax : r.yMax) * 100f) / 100f);
        }
        return new List<float>(set);
    }

    // ------------------------------------------------------------------
    // Fachadas
    // ------------------------------------------------------------------
    private void GlassStory(Edge e, float z0, float z1)
    {
        float h = z1 - z0 - 0.35f;   // bajo la banda de la losa
        Box(e, 0.5f, z0 + 0.5f * h, e.Length, h, 0.03f, 0.10f, Mat("glass", GlassTint, 0.95f));
        int n = Mathf.Max(1, Mathf.RoundToInt(e.Length / 1.5f));
        for (int k = 0; k <= n; k++)
            Box(e, k / (float)n, z0 + 0.5f * h, 0.07f, h, 0.12f, 0.12f, Mat("mullion", Mullion, 0.5f));
        Box(e, 0.5f, z0 + 0.45f * (z1 - z0), e.Length, 0.06f, 0.10f, 0.12f, Mat("mullion", Mullion, 0.5f));   // travesano
    }

    private void OrangeStory(Edge e, float z0, float z1)
    {
        float h = z1 - z0 - 0.30f;
        Box(e, 0.5f, z0 + 0.5f * h, e.Length, h, 0.12f, 0.06f, Mat("orange", Orange, 0.15f));
        int bays = Mathf.Max(1, Mathf.RoundToInt(e.Length / 2.6f));
        float bay = e.Length / bays;
        float winW = Mathf.Min(1.15f, bay * 0.45f), winH = Mathf.Min(1.7f, h - 0.9f);
        for (int k = 0; k < bays; k++)
        {
            float s = (k + 0.5f) / bays;
            float zc = z0 + 0.9f + 0.5f * winH;
            Box(e, s, zc, winW + 0.12f, winH + 0.12f, 0.03f, 0.135f, Mat("white", White, 0.3f));
            Box(e, s, zc, winW, winH, 0.03f, 0.15f, Mat("window", WindowTint, 0.85f));
        }
        for (int k = 0; k <= bays; k++)
            Box(e, k / (float)bays, z0 + 0.5f * h, 0.30f, h, 0.55f, 0.36f, Mat("orangeDark", OrangeDark, 0.15f));
    }

    /// Banda en el borde de cada losa (alero o canto de losa).
    private void SlabBand(Edge e, float z, bool glass)
    {
        if (glass) Box(e, 0.5f, z - 0.18f, e.Length + 0.05f, 0.40f, 0.30f, 0.12f, Mat("concrete", Concrete, 0.2f));
        else Box(e, 0.5f, z - 0.15f, e.Length + 0.3f, 0.30f, 0.75f, 0.30f, Mat("white", White, 0.3f));
    }

    private void Parapet(Edge e, float z)
    {
        Box(e, 0.5f, z + 0.45f, e.Length + 0.2f, 0.9f, 0.20f, 0.10f, Mat("concrete", Concrete, 0.2f));
    }

    private void Roof(float z)
    {
        Material m = Mat("techo", new Color(0.70f, 0.71f, 0.72f), 0.2f);
        foreach (Rect r in SlabRects(z))
            Cube(new Vector3(r.center.x, z + 0.12f, r.center.y), new Vector3(r.width + 0.02f, 0.12f, r.height + 0.02f), Quaternion.identity, m);
    }

    private void RoofEquipment(float z)
    {
        // equipos de clima sobre el techo de cada edificio (como en la foto aerea)
        foreach (var (x, y, sx, sy) in new[] { (5f, 2f, 4f, 2.2f), (12f, 2f, 3f, 2.2f), (20f, 3f, 5f, 2.5f), (-25f, 2f, 4f, 2.2f), (-18f, 3f, 3f, 2f) })
            Cube(new Vector3(x, z + 0.8f, y), new Vector3(sx, 1.6f, sy), Quaternion.identity, Mat("equipo", new Color(0.72f, 0.74f, 0.77f), 0.4f));
    }

    /// Caja alineada con un borde: s = posicion relativa a lo largo del borde, zc = centro en altura,
    /// largo (a lo largo), alto, espesor (normal al borde) y salida = distancia del centro hacia afuera.
    private void Box(Edge e, float s, float zc, float length, float height, float thick, float outward, Material m)
    {
        Vector2 p = e.At(s) + e.normal * outward;
        Quaternion rot = Quaternion.LookRotation(new Vector3(e.normal.x, 0f, e.normal.y), Vector3.up);
        Cube(new Vector3(p.x, zc, p.y), new Vector3(length, height, thick), rot, m);
    }

    // ------------------------------------------------------------------
    // Escaleras segun los planos 2017_67-500 a 503
    // ------------------------------------------------------------------
    /// Tramo recto a lo largo de x: peldanos, losa inclinada naranja debajo y baranda maciza naranja
    /// al exterior (y = yOut). x0 -> x1 sube de z0 a z1; ancho entre yA y yB.
    private void Flight(float x0, float x1, float z0, float z1, int steps, float yA, float yB, float yOut, bool parapet = true)
    {
        Material conc = Mat("concrete", Concrete, 0.2f), orange = Mat("orange", Orange, 0.15f);
        float run = x1 - x0, rise = z1 - z0, width = Mathf.Abs(yB - yA), yc = 0.5f * (yA + yB);
        for (int i = 0; i < steps; i++)
        {
            float xc = x0 + (i + 0.5f) * run / steps;
            float zt = z0 + (i + 1) * rise / steps;
            Cube(new Vector3(xc, zt - 0.5f * rise / steps, yc), new Vector3(Mathf.Abs(run) / steps + 0.01f, rise / steps, width), Quaternion.identity, conc);
        }
        float L = Mathf.Sqrt(run * run + rise * rise);
        Quaternion rot = Quaternion.Euler(0f, 0f, Mathf.Atan2(rise, run) * Mathf.Rad2Deg);
        Vector3 mid = new Vector3(0.5f * (x0 + x1), 0.5f * (z0 + z1), yc);
        Cube(mid + new Vector3(0f, -0.22f, 0f), new Vector3(L, 0.25f, width + 0.2f), rot, orange);                       // losa / zanca
        if (parapet)
            Cube(new Vector3(mid.x, mid.y + 0.55f, yOut), new Vector3(L, 1.1f, 0.15f), rot, orange);                   // baranda
    }

    private void Landing(float x0, float x1, float z, float yA, float yB, float yOut)
    {
        Material orange = Mat("orange", Orange, 0.15f), conc = Mat("concrete", Concrete, 0.2f);
        float xc = 0.5f * (x0 + x1), w = Mathf.Abs(x1 - x0), yc = 0.5f * (yA + yB);
        Cube(new Vector3(xc, z - 0.12f, yc), new Vector3(w, 0.24f, Mathf.Abs(yB - yA)), Quaternion.identity, conc);
        Cube(new Vector3(xc, z - 0.36f, yc), new Vector3(w, 0.25f, Mathf.Abs(yB - yA) + 0.2f), Quaternion.identity, orange);
        Cube(new Vector3(xc, z + 0.55f, yOut), new Vector3(w, 1.1f, 0.15f), Quaternion.identity, orange);
    }

    /// 2017_67-502: graderias (8 de 1,20 m) con escalera paralela de 24 peldanos (1,50 m), de la plaza
    /// (z = 0) a la terraza del piso 1 (z = 3,96), entre H - 4,67 m y H' subiendo hacia el este.
    private void Graderias()
    {
        float x0 = 20f - 4.67f, x1 = 24.477f, zTop = FloorH;
        float yStair0 = StairY0, yStair1 = StairY0 - 1.50f, yG1 = yStair1 - 5.75f;
        Material conc = Mat("concrete", Concrete, 0.2f), orange = Mat("orange", Orange, 0.15f);
        for (int g = 0; g < 8; g++)
        {
            float xs = x0 + g * 1.20f, h = (g + 1) * zTop / 8f;
            Cube(new Vector3(0.5f * (xs + x1), 0.5f * h, 0.5f * (yStair1 + yG1)), new Vector3(x1 - xs, h, yStair1 - yG1), Quaternion.identity, conc);
        }
        Flight(x0, x1, 0f, zTop, 24, yStair0, yStair1, yStair0, false);
        // muro lateral naranja al sur de las graderias y terraza del piso 1 sobre columnas
        float L = Mathf.Sqrt((x1 - x0) * (x1 - x0) + zTop * zTop);
        Cube(new Vector3(0.5f * (x0 + x1), 0.5f * zTop + 0.5f, yG1 - 0.1f), new Vector3(L, 1.0f, 0.2f), Quaternion.Euler(0f, 0f, Mathf.Atan2(zTop, x1 - x0) * Mathf.Rad2Deg), orange);
        float tx0 = x1, tx1 = 30.5f;
        Cube(new Vector3(0.5f * (tx0 + tx1), zTop - 0.15f, 0.5f * (yStair0 + yG1)), new Vector3(tx1 - tx0, 0.3f, yStair0 - yG1), Quaternion.identity, conc);
        Cube(new Vector3(0.5f * (tx0 + tx1), zTop + 0.55f, yG1 - 0.1f), new Vector3(tx1 - tx0, 1.1f, 0.2f), Quaternion.identity, orange);
        Cube(new Vector3(tx1 + 0.1f, zTop + 0.55f, 0.5f * (yStair0 + yG1)), new Vector3(0.2f, 1.1f, yStair0 - yG1), Quaternion.identity, orange);
        Material col = Mat("concrete", Concrete, 0.2f);
        foreach (float cx in new[] { 26.5f, 29.8f })
            foreach (float cy in new[] { yStair0 - 1.5f, yG1 + 0.6f })
                Cube(new Vector3(cx, 0.5f * zTop, cy), new Vector3(0.4f, zTop, 0.4f), Quaternion.identity, col);
    }

    /// 2017_67-501: escaleras rectas sobre el eje 3, cada una con descanso a media altura.
    private void ExteriorStairs()
    {
        float ya = StairY0, yb = StairY1, yOut = StairY1 - 0.08f;
        // piso 1 -> 2 (corte A): de x = H + 7,55 (z 3,96) a x = H + 0,35 (z 7,92)
        Flight(27.55f, 24.55f, FloorH, FloorH + 1.98f, 11, ya, yb, yOut);
        Landing(24.55f, 23.35f, FloorH + 1.98f, ya, yb, yOut);
        Flight(23.35f, 20.35f, FloorH + 1.98f, 2f * FloorH, 11, ya, yb, yOut);
        Landing(20.35f, 18.6f, 2f * FloorH, ya, yb, yOut);
        // piso 2 -> 3 (corte B): de x = G - 0,30 (z 7,92) a x = F + 2,50 (z 11,88), sobre el voladizo
        Landing(11.0f, 9.70f, 2f * FloorH, ya, yb, yOut);
        Flight(9.70f, 6.70f, 2f * FloorH, 2f * FloorH + 1.98f, 11, ya, yb, yOut);
        Landing(6.70f, 5.50f, 2f * FloorH + 1.98f, ya, yb, yOut);
        Flight(5.50f, 2.50f, 2f * FloorH + 1.98f, 3f * FloorH, 11, ya, yb, yOut);
    }

    /// 2017_67-503: escalera norte entre muros de contencion (ejes H2 a IB, entre 1A y 1BB), del nivel
    /// bajo (z = 0) al terreno alto (z = 4,01), 12 + 11 peldanos de 30,5 cm con descanso de 2,94 m.
    private void NorthStair()
    {
        float yA = 12.474f, yB = 15.124f, x0 = 28.825f - 3.635f;
        float r = 4.01f / 25f;
        Flight(x0, x0 + 3.66f, 0f, 13f * r, 13, yA, yB, yB + 0.1f, false);
        Material conc = Mat("concrete", Concrete, 0.2f);
        Cube(new Vector3(x0 + 3.66f + 1.4675f, 13f * r - 0.12f, 0.5f * (yA + yB)), new Vector3(2.935f, 0.24f, yB - yA), Quaternion.identity, conc);
        Flight(x0 + 6.595f, x0 + 9.95f, 13f * r, 4.01f, 12, yA, yB, yB + 0.1f, false);
        Material wall = Mat("muro", new Color(0.66f, 0.66f, 0.64f), 0.1f);
        Cube(new Vector3(x0 + 3.3f, 2.4f, yB + 0.1f), new Vector3(6.6f, 4.8f, 0.2f), Quaternion.identity, wall);   // muro norte
        Cube(new Vector3(x0 + 1.83f, 2.4f, yA - 0.1f), new Vector3(3.66f, 4.8f, 0.2f), Quaternion.identity, wall); // muro sur
        Cube(new Vector3(x0 + 10.15f, 2.4f, 0.5f * (yA + yB)), new Vector3(0.3f, 4.8f, yB - yA + 1.2f), Quaternion.identity, wall);
        // terreno alto al que llega la escalera (supuesto: los planos no traen la topografia)
        Material grass = Mat("pasto", Color.white, 0.05f);
        float yc = 0.5f * (yA + yB), xp = x0 + 10.3f, xe = x0 + 14.5f, run = 12f, h = 4.0f;
        Cube(new Vector3(0.5f * (xp + xe), 0.5f * h - 0.05f, yc), new Vector3(xe - xp, h, 12f), Quaternion.identity, grass);
        float a = -Mathf.Atan2(h, run);   // talud hacia el este hasta el nivel del pasto
        Vector3 n = new Vector3(-Mathf.Sin(a), Mathf.Cos(a), 0f);
        Vector3 mid = new Vector3(xe + 0.5f * run, 0.5f * h - 0.05f, yc) - n * 2f;
        Cube(mid, new Vector3(Mathf.Sqrt(run * run + h * h), 4f, 12f), Quaternion.Euler(0f, 0f, a * Mathf.Rad2Deg), grass);
    }

    /// 2017_67-500: escalera interior en U del nucleo (ejes Ea - Ed, 2 - 2a), dos tramos de 11 peldanos y
    /// descanso de 1,58 m, del 1er subterraneo al piso 4 (se ve a traves del vidrio).
    private void CoreStair()
    {
        Material conc = Mat("concrete", Concrete, 0.2f);
        float yTop = -0.365f, yLand = -3.365f, yWall = -4.946f;
        for (float z = 0f; z < 4f * FloorH - 0.1f; z += FloorH)
        {
            // tramo este baja-sube hacia el descanso, tramo oeste vuelve al eje 2
            for (int i = 0; i < 11; i++)
            {
                float y0 = yTop - i * 0.30f, zt = z + (i + 1) * 0.18f;
                Cube(new Vector3(-4.15f, zt - 0.09f, y0 - 0.15f), new Vector3(1.5f, 0.18f, 0.30f), Quaternion.identity, conc);
                float y1 = yLand + i * 0.30f, zt2 = z + 1.98f + (i + 1) * 0.18f;
                Cube(new Vector3(-5.85f, zt2 - 0.09f, y1 + 0.15f), new Vector3(1.5f, 0.18f, 0.30f), Quaternion.identity, conc);
            }
            Cube(new Vector3(-5.0f, z + 1.98f - 0.1f, 0.5f * (yLand + yWall)), new Vector3(3.2f, 0.2f, yLand - yWall), Quaternion.identity, conc);
        }
    }

    // ------------------------------------------------------------------
    // Entorno
    // ------------------------------------------------------------------
    private void Plaza()
    {
        Material m = Mat("plaza", new Color(0.70f, 0.69f, 0.66f), 0.1f);
        Flat(new Vector3(9f, -0.04f, -13.5f), new Vector2(46f, 12f), m);      // plaza baja frente al vidrio
        Flat(new Vector3(-26f, -0.04f, -10.8f), new Vector2(33f, 7f), m);     // frente del edificio 2
        Flat(new Vector3(17f, -0.045f, -40f), new Vector2(3.5f, 40f), m);     // camino hacia el sur
        // quitasoles y mesas en la plaza (foto aerea), fuera del voladizo
        Material pole = Mat("poste", new Color(0.35f, 0.35f, 0.37f), 0.4f), canopy = Mat("toldo", new Color(0.55f, 0.56f, 0.58f), 0.2f);
        foreach (var (x, y) in new[] { (9f, -12.8f), (12.5f, -12.8f), (9f, -16.3f), (12.5f, -16.3f), (5.5f, -16.3f) })
        {
            Cylinder(new Vector3(x, 1.2f, y), new Vector3(0.08f, 1.2f, 0.08f), pole);
            Cylinder(new Vector3(x, 2.45f, y), new Vector3(2.6f, 0.05f, 2.6f), canopy);
            Cylinder(new Vector3(x, 0.38f, y), new Vector3(0.9f, 0.38f, 0.9f), pole);
        }
    }

    private void Ground()
    {
        var tex = new Texture2D(128, 128, TextureFormat.RGB24, true) { wrapMode = TextureWrapMode.Repeat };
        for (int i = 0; i < 128; i++)
            for (int j = 0; j < 128; j++)
            {
                float n = Mathf.PerlinNoise(i * 0.09f, j * 0.09f) * 0.6f + Mathf.PerlinNoise(i * 0.35f, j * 0.35f) * 0.4f;
                tex.SetPixel(i, j, Color.Lerp(new Color(0.30f, 0.50f, 0.22f), new Color(0.47f, 0.66f, 0.30f), n));
            }
        tex.Apply();
        Material grass = Mat("pasto", Color.white, 0.05f);
        grass.mainTexture = tex;
        grass.mainTextureScale = new Vector2(30f, 18f);
        Flat(new Vector3(0f, -0.06f, -5f), new Vector2(220f, 130f), grass);
    }

    private void Trees()
    {
        var rnd = new System.Random(7);
        Material trunk = Mat("tronco", new Color(0.40f, 0.29f, 0.20f), 0.1f);
        Material[] leaves = { Mat("hoja1", new Color(0.22f, 0.42f, 0.18f), 0.1f), Mat("hoja2", new Color(0.32f, 0.52f, 0.22f), 0.1f),
                              Mat("hoja3", new Color(0.40f, 0.55f, 0.26f), 0.1f) };
        int placed = 0, tries = 0;
        while (placed < 34 && tries++ < 600)
        {
            float x = (float)(rnd.NextDouble() * 150.0 - 75.0);
            float y = (float)(rnd.NextDouble() * 90.0 - 52.0);
            bool nearBuilding = x > -47f && x < 46f && y > -22f && y < 21f;
            bool onPath = Mathf.Abs(x - 17f) < 4f && y < -18f;
            if (nearBuilding || onPath) continue;
            float s = 0.8f + (float)rnd.NextDouble() * 0.6f;
            Cylinder(new Vector3(x, 1.4f * s, y), new Vector3(0.35f * s, 1.4f * s, 0.35f * s), trunk);
            Material l = leaves[rnd.Next(leaves.Length)];
            Sphere(new Vector3(x, 3.6f * s, y), new Vector3(3.6f, 3.0f, 3.6f) * s, l);
            Sphere(new Vector3(x + 0.8f * s, 4.4f * s, y + 0.4f * s), new Vector3(2.6f, 2.2f, 2.6f) * s, l);
            placed++;
        }
    }

    // ------------------------------------------------------------------
    // Primitivas sin colisionador
    // ------------------------------------------------------------------
    private void Cube(Vector3 pos, Vector3 scale, Quaternion rot, Material m) => Prim(PrimitiveType.Cube, pos, scale, rot, m);
    private void Cylinder(Vector3 pos, Vector3 scale, Material m) => Prim(PrimitiveType.Cylinder, pos, scale, Quaternion.identity, m);
    private void Sphere(Vector3 pos, Vector3 scale, Material m) => Prim(PrimitiveType.Sphere, pos, scale, Quaternion.identity, m);

    private void Flat(Vector3 pos, Vector2 size, Material m)
    {
        Prim(PrimitiveType.Quad, pos, new Vector3(size.x, size.y, 1f), Quaternion.Euler(90f, 0f, 0f), m);
    }

    private void Prim(PrimitiveType type, Vector3 pos, Vector3 scale, Quaternion rot, Material m)
    {
        GameObject g = GameObject.CreatePrimitive(type);
        g.hideFlags = HideFlags.DontSave;
        Collider c = g.GetComponent<Collider>();
        if (c != null) DestroyImmediate(c);
        g.transform.SetParent(transform, false);
        g.transform.position = pos;
        g.transform.rotation = rot;
        g.transform.localScale = scale;
        Renderer r = g.GetComponent<Renderer>();
        r.sharedMaterial = m;
        r.shadowCastingMode = type == PrimitiveType.Quad ? UnityEngine.Rendering.ShadowCastingMode.Off : UnityEngine.Rendering.ShadowCastingMode.On;
    }

    private Material Mat(string key, Color color, float smooth)
    {
        if (mats.TryGetValue(key, out Material m)) return m;
        Shader shader = Shader.Find("Standard") ?? Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Sprites/Default");
        m = new Material(shader) { color = color };
        if (m.HasProperty("_Glossiness")) m.SetFloat("_Glossiness", smooth);
        if (color.a >= 1f && key != "pasto" && m.HasProperty("_EmissionColor"))
        {
            m.EnableKeyword("_EMISSION");
            float glow = key.StartsWith("orange") || key == "white" ? 0.55f : 0.28f;   // la cara norte queda en sombra
            m.SetColor("_EmissionColor", color * glow);
        }
        if (color.a < 1f)
        {
            m.SetFloat("_Mode", 3f);
            m.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
            m.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            m.SetInt("_ZWrite", 0);
            m.DisableKeyword("_ALPHATEST_ON");
            m.EnableKeyword("_ALPHABLEND_ON");
            m.renderQueue = 3000;
        }
        mats[key] = m;
        return m;
    }

    private void OnDestroy()
    {
        foreach (Material m in mats.Values) if (m != null) Destroy(m);
        if (instance == this) instance = null;
    }
}
