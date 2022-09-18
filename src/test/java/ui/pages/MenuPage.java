package ui.pages;

import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;
import ui.DriverManager;

public class MenuPage {
    @FindBy(xpath = "//a[@data-target='#s-menu-users']")
    private WebElement usersLink;
    @FindBy(xpath = "//a[.='Players']")
    private WebElement playersLink;

    public MenuPage() {
        PageFactory.initElements(DriverManager.getDriver(), this);
    }

    public MenuPage clickUsers() {
        usersLink.click();
        return this;
    }

    public void clickPlayers() {
        playersLink.click();
    }
}
