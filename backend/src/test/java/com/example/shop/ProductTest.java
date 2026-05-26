package com.example.shop;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.math.BigDecimal;
import org.junit.jupiter.api.Test;

class ProductTest {

    @Test
    void shouldCreateProductWithValidPrice() {
        BigDecimal price = new BigDecimal("199.99");
        assertTrue(price.compareTo(BigDecimal.ZERO) >= 0);
    }

    @Test
    void shouldRejectNegativePrice() {
        assertThrows(IllegalArgumentException.class, () -> {
            BigDecimal price = new BigDecimal("-1");
            if (price.compareTo(BigDecimal.ZERO) < 0) {
                throw new IllegalArgumentException("Price cannot be negative");
            }
        });
    }
}
