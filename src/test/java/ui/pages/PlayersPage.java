package ui.pages;

import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;
import ui.DriverManager;

import java.util.Comparator;

public class PlayersPage {

    @FindBy(xpath = "//table")
    private WebElement playerTable;
    @FindBy(xpath = "//strong[contains(.,'Player management')]")
    private WebElement header;

    public PlayersPage() {
        PageFactory.initElements(DriverManager.getDriver(), this);
        playerTable.isDisplayed();
        header.isDisplayed();
    }

    public void sortByColumn(String column, String sort) {
        new Table(playerTable).checkSortByColumn(column, getComparator(sort));
    }

    public static Comparator<String> getComparator(String type) {
        if (type.equals("STRING_ASC"))
            return Comparator.naturalOrder();
        throw new Error("Не найден comparator для " + type);
    }

}
