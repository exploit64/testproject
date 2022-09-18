package api.steps;

import io.restassured.RestAssured;
import io.restassured.specification.RequestSpecification;

public class RestAssuredConfig {

    public static RequestSpecification baseSpec() {
        return RestAssured.given()
                .baseUri(utils.Config.get("api.url"))
                .contentType("application/json")
                .log()
                .all();
    }
}
