package ui.pages;

import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import ui.DriverManager;

import java.time.Duration;

public class LoginPage {
    @FindBy(xpath = "//input[@placeholder='Login']")
    private WebElement loginField;
    @FindBy(xpath = "//input[@placeholder='Password']")
    private WebElement passwordField;
    @FindBy(xpath = "//input[@value='Sign in']")
    private WebElement singInSubmit;


    public LoginPage() {
        PageFactory.initElements(DriverManager.getDriver(), this);
    }

    public void LogIn(String username, String password){
        loginField.sendKeys(username);
        passwordField.sendKeys(password);
        singInSubmit.click();
        new WebDriverWait(DriverManager.getDriver(), Duration.ofSeconds(5)).until(ExpectedConditions.invisibilityOf(passwordField));
    }
}
