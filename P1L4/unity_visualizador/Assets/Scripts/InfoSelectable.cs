using UnityEngine;

public class InfoSelectable : MonoBehaviour
{
    public string info;

    public string GetInfo()
    {
        return string.IsNullOrEmpty(info) ? "Objeto sin informacion." : info;
    }
}
