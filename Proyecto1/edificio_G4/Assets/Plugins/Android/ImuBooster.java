package cl.uandes.mcoc;

import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.Handler;
import android.os.HandlerThread;

/**
 * Semana 6 (AR): en el Galaxy S24 la sesion ARCore dentro de Unity se quedaba
 * con el giroscopio y el acelerometro a la tasa minima (160 ms = 6,25 Hz) y el
 * tracking visual-inercial derivaba. El sensor fisico trabaja a la tasa mas
 * rapida pedida por cualquier cliente, asi que este listener vacio a 5 ms
 * (200 Hz) hace que ARCore reciba tambien sus muestras a 200 Hz.
 */
public final class ImuBooster implements SensorEventListener {
    private static final int PERIOD_US = 5000;
    private static final int[] TYPES = {
        Sensor.TYPE_GYROSCOPE_UNCALIBRATED,
        Sensor.TYPE_ACCELEROMETER_UNCALIBRATED,
        Sensor.TYPE_GYROSCOPE,
        Sensor.TYPE_ACCELEROMETER
    };

    private static ImuBooster instance;
    private final SensorManager manager;
    private final HandlerThread thread;
    private final Handler handler;

    private ImuBooster(Context context) {
        manager = (SensorManager) context.getSystemService(Context.SENSOR_SERVICE);
        thread = new HandlerThread("ImuBooster");
        thread.start();
        handler = new Handler(thread.getLooper());
    }

    /** Devuelve cuantos sensores quedaron registrados. */
    public static synchronized int start(Context context) {
        if (instance == null) instance = new ImuBooster(context.getApplicationContext());
        return instance.register();
    }

    public static synchronized void stop() {
        if (instance != null) instance.manager.unregisterListener(instance);
    }

    private int register() {
        manager.unregisterListener(this);
        int count = 0;
        for (int type : TYPES) {
            Sensor sensor = manager.getDefaultSensor(type);
            if (sensor != null && manager.registerListener(this, sensor, PERIOD_US, handler)) count++;
        }
        return count;
    }

    @Override public void onSensorChanged(SensorEvent event) { }
    @Override public void onAccuracyChanged(Sensor sensor, int accuracy) { }
}
