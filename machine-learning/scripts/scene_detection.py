import cv2

def is_scene_change(prev_hist, curr_hist, threshold=0.5):
    # Вычисление расстояния между гистограммами
    diff = cv2.compareHist(prev_hist, curr_hist, cv2.HISTCMP_CORREL)
    return diff < threshold
