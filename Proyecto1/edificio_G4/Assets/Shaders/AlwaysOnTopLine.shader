Shader "Custom/AlwaysOnTopLine"
{
    Properties
    {
        _Color ("Color", Color) = (1,1,1,1)
    }
    SubShader
    {
        Tags { "Queue"="Overlay" "RenderType"="Transparent" "IgnoreProjector"="True" }
        Pass
        {
            ZWrite Off
            ZTest Always
            Blend SrcAlpha OneMinusSrcAlpha
            Color [_Color]
        }
    }
    Fallback Off
}