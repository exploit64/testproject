package api.steps;

import api.models.Player;
import api.models.PlayerRegisterData;
import com.fasterxml.jackson.databind.PropertyNamingStrategy;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import io.restassured.RestAssured;
import io.restassured.specification.RequestSpecification;
import lombok.Builder;
import lombok.Getter;

import static io.restassured.module.jsv.JsonSchemaValidator.matchesJsonSchemaInClasspath;

public class PlayerSteps {
    private final PlayerRegisterData data;

    public PlayerSteps(PlayerRegisterData data) {
        this.data = data;
    }

    private RequestSpecification playerSpec() {
        return RestAssuredConfig.baseSpec().auth().oauth2(getPlayerToken());
    }

    public String getPlayerToken() {
        return RestAssured.given()
                .spec(GuestSteps.guestBasicSpec())
                .body(PlayerAuth.builder().username(data.getUsername()).password(data.getPasswordChange()).build())
                .post("/v2/oauth2/token")
                .then()
                .assertThat()
                .statusCode(200)
                .extract()
                .jsonPath()
                .getString("access_token");
    }

    public Player getPlayer(int playerId) {
        return RestAssured.given()
                .spec(playerSpec())
                .get("/v2/players/" + playerId)
                .then()
                .assertThat()
                .body(matchesJsonSchemaInClasspath("schema/player.json"))
                .statusCode(200)
                .extract()
                .as(Player.class);
    }

    @Getter
    @Builder
    @JsonNaming(PropertyNamingStrategy.SnakeCaseStrategy.class)
    public static class PlayerAuth {
        @Builder.Default
        String grantType = "password";
        String username;
        String password;
    }
}
