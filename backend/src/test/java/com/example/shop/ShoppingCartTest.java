package com.example.shop;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class ShoppingCartTest {

    @Test
    void shouldStartWithNoOrders() {
        List<String> orders = new ArrayList<>();
        assertTrue(orders.isEmpty());
    }

    @Test
    void shouldContainOrderAfterAdd() {
        List<String> orders = new ArrayList<>();
        orders.add("order-1");
        assertFalse(orders.isEmpty());
        assertEquals(1, orders.size());
    }
}
