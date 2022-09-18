package api.steps;

import api.models.Player;
import api.models.PlayerRegisterData;
import com.fasterxml.jackson.databind.PropertyNamingStrategy;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import io.restassured.RestAssured;
import io.restassured.specification.RequestSpecification;
import lombok.Getter;

import java.util.Random;

import static io.restassured.module.jsv.JsonSchemaValidator.matchesJsonSchemaInClasspath;

public class GuestSteps {

    public static RequestSpecification guestBasicSpec() {
        return RestAssuredConfig.baseSpec().auth().preemptive().basic(utils.Config.get("guest.login"), "");
    }

    public static RequestSpecification guestSpec() {
        return RestAssuredConfig.baseSpec().auth().oauth2(getGuestToken());
    }

    public static String getGuestToken() {
        return RestAssured.given().spec(guestBasicSpec())
                .body(new GuestAuth())
                .post("/v2/oauth2/token")
                .then()
                .assertThat()
                .statusCode(200)
                .extract()
                .jsonPath()
                .getString("access_token");
    }

    public static PlayerRegisterData generatePlayerRegisterData() {
        String username = "User" + new Random().nextInt();
        String password = "amFuZWRvZTEyMw==";
        return PlayerRegisterData.builder()
                .username(username)
                .email(username + "@gmail.com")
                .name("name")
                .surname("surname")
                .passwordChange(password)
                .passwordRepeat(password)
                .build();
    }

    public static Player createPlayer(PlayerRegisterData data) {
        return RestAssured.given().spec(guestSpec())
                .body(data)
                .post("/v2/players")
                .then()
                .assertThat()
                .statusCode(201)
                .body(matchesJsonSchemaInClasspath("schema/player.json"))
                .extract()
                .as(Player.class);
    }

    @Getter
    @JsonNaming(PropertyNamingStrategy.SnakeCaseStrategy.class)
    public static class GuestAuth {
        String grantType = "client_credentials";
        String scope = "guest:default";
    }
}
