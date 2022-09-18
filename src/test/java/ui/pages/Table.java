package ui.pages;

import org.junit.jupiter.api.Assertions;
import org.openqa.selenium.By;
import org.openqa.selenium.NotFoundException;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import ui.DriverManager;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;

public class Table {
    private final WebElement table;

    public Table(WebElement table) {
        this.table = table;
        By loading = By.xpath("//div[contains(@class, 'grid-view-loading')]");
        new WebDriverWait(DriverManager.getDriver(), Duration.ofSeconds(5)).until(ExpectedConditions.invisibilityOfElementLocated(loading));
    }

    public List<String> getTextsInColumn(String columnName) {
        List<WebElement> cells = table.findElements(By.xpath(String.format("//table/tbody/tr/td[%s]", getColumnIndex(columnName) + 1)));
        return cells.stream().map(WebElement::getText).collect(Collectors.toList());
    }

    public int getColumnIndex(String columnName) {
        List<WebElement> headers = table.findElements(By.xpath("//thead/tr/th"));
        for (int i = 0; i < headers.size(); i++) {
            if (headers.get(i).getText().equals(columnName))
                return i;
        }
        throw new NotFoundException("В таблице не найдена колонка " + columnName);
    }

    public void checkSortByColumn(String columnName, Comparator<String> comparator) {
        List<String> texts = getTextsInColumn(columnName);
        List<String> sortedTexts = new ArrayList<>(texts);
        sortedTexts.sort(comparator);
        Assertions.assertEquals(sortedTexts, texts);
    }

}
