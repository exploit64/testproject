package ui;

import io.github.bonigarcia.wdm.WebDriverManager;
import org.openqa.selenium.Dimension;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import utils.Config;

import java.time.Duration;

public class DriverManager {
    private static final ThreadLocal<WebDriver> webDriver = new ThreadLocal<>();

    public static void setDriver() {
        WebDriverManager.chromedriver().setup();
        WebDriver driver = new ChromeDriver();
        driver.manage()
                .window()
                .setSize(new Dimension(Integer.parseInt(Config.get("browser.width")), Integer.parseInt(Config.get("browser.height"))));
        driver.manage()
                .timeouts()
                .implicitlyWait(Duration.ofSeconds(5));
        webDriver.set(driver);
    }

    public static WebDriver getDriver() {
        return webDriver.get();
    }

    public static void close() {
        webDriver.get().close();
        webDriver.remove();
    }
}
