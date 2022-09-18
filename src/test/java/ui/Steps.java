package ui;

import io.cucumber.java.ru.*;
import org.openqa.selenium.By;
import ui.pages.LoginPage;
import ui.pages.MenuPage;
import ui.pages.PlayersPage;
import utils.Config;

public class Steps {

    @Пусть("^пользователь (.*) авторизуется в админке$")
    public void singIn(String username) {
        DriverManager.getDriver().get(Config.get("admin.url"));
        new LoginPage().LogIn(username, Config.get("admin.password." + username));
    }

    @Затем("^пользователь нажимает на ссылку (.*)$")
    public void openLink(String name) {
        DriverManager.getDriver().findElement(By.xpath(String.format("//a[.='%s']", name))).click();
    }

    @Если("^пользователь открывает список игроков$")
    public void openPlayerManagement() {
        new MenuPage()
                .clickUsers()
                .clickPlayers();
    }

    @Тогда("^открывается страница PLAYER MANAGEMENT$")
    public void checkPlayerManagement() {
        new PlayersPage();
    }

    @То("^таблица PLAYER MANAGEMENT отсортирована по колонке (.*) в порядке (.*)$")
    public void sortTable(String column, String sort) {
        new PlayersPage().sortByColumn(column, sort);
    }

}
