using UnityEngine;

public static class UiTheme
{
    // Layout coordinado: todas las zonas se derivan de estas constantes
    // para que NINGUN panel se superponga a otro.
    public const float TopBarH = 86f;
    public const float SideM = 12f;
    public const float CtrlW = 348f;
    public const float Gap = 16f;

    // Paleta "plano tecnico / blueprint"
    public static readonly Color PanelBg = new Color(0.035f, 0.05f, 0.095f, 0.97f);
    public static readonly Color Accent = new Color(0.27f, 0.85f, 1f, 1f);
    public static readonly Color AccentDim = new Color(0.18f, 0.55f, 0.85f, 1f);
    public static readonly Color Accent2 = new Color(1f, 0.78f, 0.35f, 1f);
    public static readonly Color TextMain = new Color(0.93f, 0.96f, 1f, 1f);
    public static readonly Color TextDim = new Color(0.6f, 0.72f, 0.88f, 1f);

    static GUIStyle _panelBox;
    static GUIStyle _titleSm;
    static GUIStyle _label;
    static GUIStyle _labelBold;
    static GUIStyle _header;
    static GUIStyle _dimLabel;
    static GUIStyle _brand;
    static Texture2D _panelTex;
    static Texture2D _stripTex;
    static Texture2D _whiteTex;
    static Font _mono;

    public static float LeftHeight
    {
        get
        {
            float avail = Screen.height - TopBarH - 8f;
            float maxLeft = 520f;
            float reservedPm = 372f;
            return Mathf.Clamp(avail - reservedPm, 250f, maxLeft);
        }
    }

    public static float InfoWidth
    {
        get { return Mathf.Clamp(Screen.width * 0.26f, 372f, 455f); }
    }

    public static float InfoLeft
    {
        get { return Screen.width - SideM - InfoWidth; }
    }

    public static Rect LeftArea()
    {
        return new Rect(SideM, TopBarH + 8f, CtrlW, LeftHeight);
    }

    public static Rect InfoPanel()
    {
        float w = InfoWidth;
        return new Rect(Screen.width - SideM - w, TopBarH + 8f, w, Screen.height - TopBarH - 8f);
    }

    public static Rect PMArea()
    {
        float x = SideM + CtrlW + Gap;
        float y = TopBarH + 8f + LeftHeight + 14f;
        float available = InfoLeft - Gap - x;
        float pw = Mathf.Min(430f, Mathf.Min(Screen.width * 0.4f, available));
        if (pw < 300f) pw = 300f;
        float ph = Screen.height - y - 12f;
        if (ph < 280f) ph = 280f;
        return new Rect(x, y, pw, ph);
    }

    public static Rect CenterTop(float w, float h)
    {
        float left = SideM + CtrlW + Gap;
        float right = InfoLeft - Gap;
        float span = right - left;
        if (span < w) w = Mathf.Max(210f, span);
        float x = left + (span - w) * 0.5f;
        return new Rect(x, TopBarH + 8f + 4f, w, h);
    }

    public static Texture2D White()
    {
        if (_whiteTex != null) return _whiteTex;
        _whiteTex = MakeTex(Color.white, 1, 1);
        return _whiteTex;
    }

    public static Texture2D MakeTex(Color color, int w = 1, int h = 1)
    {
        var tex = new Texture2D(w, h);
        for (int y = 0; y < h; y++)
            for (int x = 0; x < w; x++)
                tex.SetPixel(x, y, color);
        tex.Apply();
        return tex;
    }

    public static void GUIBox(Rect rect, string title = null)
    {
        GUI.Box(rect, GUIContent.none, PanelBox);
        GUI.DrawTexture(new Rect(rect.x, rect.y, rect.width, 3f), Strip);
        GUI.DrawTexture(new Rect(rect.x, rect.y, 3f, rect.height), Strip);
        if (!string.IsNullOrEmpty(title))
        {
            GUI.Label(new Rect(rect.x + 10f, rect.y + 7f, rect.width - 20f, 18f), title, TitleSm);
        }
    }

    static GUIStyle PanelBox
    {
        get
        {
            if (_panelBox == null)
            {
                _panelBox = new GUIStyle(GUI.skin.box);
                _panelBox.normal.background = PanelTex;
                _panelBox.border = new RectOffset(2, 2, 2, 2);
                _panelBox.padding = new RectOffset(8, 8, 8, 8);
            }
            return _panelBox;
        }
    }

    public static GUIStyle Label
    {
        get
        {
            if (_label == null)
            {
                _label = new GUIStyle(GUI.skin.label);
                _label.font = Monospace;
                _label.fontSize = 12;
                _label.normal.textColor = TextMain;
                _label.wordWrap = true;
                _label.richText = false;
                _label.alignment = TextAnchor.UpperLeft;
                _label.padding = new RectOffset(0, 0, 0, 0);
            }
            return _label;
        }
    }

    public static GUIStyle LabelBold
    {
        get
        {
            if (_labelBold == null)
            {
                _labelBold = new GUIStyle(Label);
                _labelBold.fontStyle = FontStyle.Bold;
                _labelBold.normal.textColor = TextMain;
            }
            return _labelBold;
        }
    }

    public static GUIStyle TitleSm
    {
        get
        {
            if (_titleSm == null)
            {
                _titleSm = new GUIStyle(Label);
                _titleSm.fontSize = 13;
                _titleSm.fontStyle = FontStyle.Bold;
                _titleSm.normal.textColor = Accent;
            }
            return _titleSm;
        }
    }

    public static GUIStyle Header
    {
        get
        {
            if (_header == null)
            {
                _header = new GUIStyle(Label);
                _header.fontSize = 11;
                _header.fontStyle = FontStyle.Bold;
                _header.normal.textColor = Accent2;
            }
            return _header;
        }
    }

    public static GUIStyle DimLabel
    {
        get
        {
            if (_dimLabel == null)
            {
                _dimLabel = new GUIStyle(Label);
                _dimLabel.normal.textColor = TextDim;
            }
            return _dimLabel;
        }
    }

    public static GUIStyle Brand
    {
        get
        {
            if (_brand == null)
            {
                _brand = new GUIStyle(Label);
                _brand.fontSize = 13;
                _brand.fontStyle = FontStyle.Bold;
                _brand.normal.textColor = Accent;
            }
            return _brand;
        }
    }

    static Texture2D PanelTex
    {
        get
        {
            if (_panelTex == null) _panelTex = MakeTex(PanelBg);
            return _panelTex;
        }
    }

    static Texture2D Strip
    {
        get
        {
            if (_stripTex == null) _stripTex = MakeTex(AccentDim);
            return _stripTex;
        }
    }

    static Font Monospace
    {
        get
        {
            if (_mono == null)
            {
                Font f = Font.CreateDynamicFontFromOSFont("Consolas", 12);
                if (f == null) f = Font.CreateDynamicFontFromOSFont(new string[] { "Consolas", "Courier New", "Liberation Mono", "DejaVu Sans Mono" }, 12);
                _mono = f ?? null;
            }
            return _mono;
        }
    }
}