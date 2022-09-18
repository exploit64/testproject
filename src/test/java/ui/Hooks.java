package ui;

import io.cucumber.java.After;
import io.cucumber.java.Before;

public class Hooks {

    @Before
    public void before() {
        DriverManager.setDriver();
    }

    @After
    public void after() {
        DriverManager.close();
    }

}
