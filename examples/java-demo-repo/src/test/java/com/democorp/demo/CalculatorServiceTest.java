// SPDX-License-Identifier: Apache-2.0

package com.democorp.demo;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class CalculatorServiceTest {
    @Test
    void addsNumbers() {
        CalculatorService service = new CalculatorService();
        assertEquals(4, service.add(2, 2));
    }
}
