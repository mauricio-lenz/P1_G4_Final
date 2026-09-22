using UnityEngine;

public class InfoSelectable : MonoBehaviour
{
    [TextArea]
    public string info;

    public string GetInfo()
    {
        return info;
    }
}
