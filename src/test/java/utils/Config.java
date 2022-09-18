package utils;

import java.io.InputStream;
import java.util.Properties;

public class Config {
    private static final Properties properties = new Properties();

    static {
        loadProperties();
    }

    private static void loadProperties() {
        try (InputStream inputStream = Config.class.getResourceAsStream("/application.properties")) {
            properties.load(inputStream);
        } catch (Exception e) {
            throw new Error("Ошибка загрузки конфиг файла application.properties: " + e.getMessage());
        }
    }

    public static String get(String propertyKey) {
        return properties.getProperty(propertyKey);
    }

}
