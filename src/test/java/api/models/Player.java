package api.models;

import com.fasterxml.jackson.databind.PropertyNamingStrategy;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

import java.util.Date;


@Data
@JsonNaming(PropertyNamingStrategy.SnakeCaseStrategy.class)
public class Player {
    Integer id;
    Integer countryId;
    Integer timezoneId;
    String username;
    String email;
    String name;
    String surname;
    String gender;
    String phoneNumber;
    Date birthdate;
    Boolean bonusesAllowed;
    Boolean isVerified;
}
