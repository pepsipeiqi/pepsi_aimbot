import numpy as np
import pyautogui
import time
from functools import partial
from math import factorial
from typing import List, Tuple, Optional
from ..core.base_driver import BaseDriver


class LADRCController:
    def __init__(self,
                 orden_proceso: int,
                 ganancia_nominal: float,
                 ancho_banda_controlador: float,
                 ancho_banda_leso: float,
                 condicion_inicial: int = 0) -> None:
        self.u = 0
        self.h = 0.001
        
        self.nx = int(orden_proceso)
        self.bo = ganancia_nominal
        self.wc = ancho_banda_controlador
        self.wo = ancho_banda_leso
        self.zo = condicion_inicial
        
        self.Cg, self.Ac, self.Bc, self.Cc, self.zo, self.L, self.K, self.z = self._construir_matrices()
    
    def _construir_matrices(self) -> tuple:
        n = self.nx + 1
        
        K = np.zeros([1, self.nx])
        for i in range(self.nx):
            K[0, i] = pow(self.wc, n - (i + 1)) * (
                (factorial(self.nx)) / (factorial((i + 1) - 1) * factorial(n - (i + 1))))
        
        L = np.zeros([n, 1])
        for i in range(n):
            L[i] = pow(self.wo, i + 1) * (
                (factorial(n)) / (factorial(i + 1) * factorial(n - (i + 1))))
        
        Cg = self.bo
        
        Ac = np.vstack((np.hstack((np.zeros([n - 1, 1]), np.identity(n - 1))), np.zeros([1, n])))
        Bc = np.vstack((np.zeros([self.nx - 1, 1]), self.bo, 0))
        Cc = np.hstack(([[1]], np.zeros([1, n - 1])))
        zo = np.vstack(([[self.zo]], np.zeros([n - 1, 1])))
        z = np.zeros([n, 1])
        
        return Cg, Ac, Bc, Cc, zo, L, K, z
    
    def _leso(self, u, y, z) -> np.ndarray:
        return np.matmul(self.Ac, z) + self.Bc * u + self.L * (y - np.matmul(self.Cc, z))
    
    def _runkut4(self, F, z, h):
        k0 = h * F(z)
        k1 = h * F(z + 0.5 * k0)
        k2 = h * F(z + 0.5 * k1)
        k3 = h * F(z + k2)
        return z + (1 / 6) * (k0 + 2 * k1 + 2 * k2 + k3)
    
    def salida_control(self, r: int, y: int):
        leso = partial(self._leso, self.u, y)
        self.z = self._runkut4(leso, self.z, self.h)
        u0 = self.K[0, 0] * (r - self.z[0, 0])
        for i in range(self.nx - 1):
            u0 -= self.K[0, i + 1] * self.z[i + 1, 0]
        
        return (u0 - self.z[self.nx, 0]) * self.Cg
    
    def move_to_target(
        self,
        driver: BaseDriver,
        x_objetivo: int,
        y_objetivo: int,
        max_attempts: int = 50,
        tolerance: int = 5,
        delay: float = 0.01
    ) -> Tuple[bool, List[Tuple[int, int]]]:
        trajectory = []
        move_attempts = 0
        
        try:
            while move_attempts < max_attempts:
                x_actual, y_actual = pyautogui.position()
                trajectory.append((x_actual, y_actual))
                error_x = x_objetivo - x_actual
                error_y = y_objetivo - y_actual
                
                if abs(error_x) < tolerance and abs(error_y) < tolerance:
                    return True, trajectory
                
                u_x = self.salida_control(error_x, x_actual)
                u_y = self.salida_control(error_y, y_actual)
                
                move_x = int(u_x)
                move_y = int(u_y)
                
                if move_x != 0 or move_y != 0:
                    if not driver.move_relative(move_x, move_y):
                        return False, trajectory
                
                time.sleep(delay)
                move_attempts += 1
            
            x_final, y_final = pyautogui.position()
            success = (abs(x_final - x_objetivo) < tolerance and 
                      abs(y_final - y_objetivo) < tolerance)
            
            return success, trajectory
        except Exception as e:
            print(f"LADRC control movement failed: {e}")
            return False, trajectory


def control_movimiento_raton(
    driver: BaseDriver,
    x_objetivo: int,
    y_objetivo: int,
    wc: float = 1.0,
    wo: float = 1.0,
    bo: float = 0.7
) -> Tuple[bool, List[Tuple[int, int]]]:
    controlador = LADRCController(
        orden_proceso=2,
        ganancia_nominal=bo,
        ancho_banda_controlador=wc,
        ancho_banda_leso=wo,
        condicion_inicial=0
    )
    
    return controlador.move_to_target(driver, x_objetivo, y_objetivo)