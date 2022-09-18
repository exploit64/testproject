package api;


import api.models.Player;
import api.models.PlayerRegisterData;
import api.steps.GuestSteps;
import api.steps.PlayerSteps;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

public class ApiTests {

    @Test
    @DisplayName("Получить токен гостя (Client Credentials Grant, scope — guest:default)")
    void getGuestTokenTest() {
        Assertions.assertNotNull(GuestSteps.getGuestToken(), "Токен отсутствует");
    }

    @Test
    @DisplayName("Зарегистрировать игрока")
    void registerPlayerTest() {
        PlayerRegisterData data = GuestSteps.generatePlayerRegisterData();
        Player createdPlayer = GuestSteps.createPlayer(data);
        Assertions.assertAll(() -> {
            Assertions.assertEquals(data.getEmail(), createdPlayer.getEmail());
            Assertions.assertEquals(data.getUsername(), createdPlayer.getUsername());
            Assertions.assertEquals(data.getSurname(), createdPlayer.getSurname());
            Assertions.assertEquals(data.getName(), createdPlayer.getName());
        });
    }

    @Test
    @DisplayName("Авторизоваться под созданным игроком (Resource Owner Password Credentials Grant)")
    void authPlayerTest() {
        PlayerRegisterData data = GuestSteps.generatePlayerRegisterData();
        GuestSteps.createPlayer(data);
        Assertions.assertNotNull(new PlayerSteps(data).getPlayerToken(), "Токен игрока отсутствует");
    }

    @Test
    @DisplayName("Запросить данные профиля игрока")
    void getPlayerDataTest() {
        PlayerRegisterData data = GuestSteps.generatePlayerRegisterData();
        Player createdPlayer = GuestSteps.createPlayer(data);
        Assertions.assertEquals(createdPlayer.getId(), new PlayerSteps(data).getPlayer(createdPlayer.getId()).getId());
    }

    @Test
    @DisplayName("Запросить данные другого игрока")
    void getOtherPlayerDataTest() {
        PlayerRegisterData data = GuestSteps.generatePlayerRegisterData();
        GuestSteps.createPlayer(data);
        Player createdOtherPlayer = GuestSteps.createPlayer(GuestSteps.generatePlayerRegisterData());
        Assertions.assertThrows(AssertionError.class, () -> new PlayerSteps(data).getPlayer(createdOtherPlayer.getId()),
                "Expected status code <200> but was <404>");
    }
}
