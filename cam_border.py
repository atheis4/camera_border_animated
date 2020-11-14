#!/usr/bin/env python3

from PIL import Image, ImageDraw, ImageFilter
import math

import constants
import guides


class Coordinates:
    CENTER = (constants.GRADIENT_WIDTH / 2, constants.GRADIENT_HEIGHT / 2)

    def __init__(self, width, height, degrees):
        self.width = width
        self.height = height
        self.degrees = degrees
        self.coords = None

    @classmethod
    def create_new(cls, width, height, degrees):
        coords = cls(width, height, degrees)
        coords.gen_coordinates()
        return coords

    def gen_coordinates(self):
        start = (0, constants.GRADIENT_HEIGHT / 2)
        end = self.invert_point(start)
        radius = self.pythagorean(self.CENTER[0], self.CENTER[1])
        coords = []
        theta = self.degrees
        while theta <= 180:
            x, y = self.CENTER
            dx = self.get_change_in_x(x, radius, theta)
            dy = self.get_change_in_y(y, radius, theta)
            # process start/end point to fix to gradient
            # start = self.adjust_to_rectangle((dx, dy))
            start = Layer.add_gradient_offset((dx, dy))
            end = self.invert_point(start)

            coords.append((start, end))
            theta += self.degrees

        self.coords = coords

    # TODO: FIX!
    def adjust_to_rectangle(point, theta):
        x, y = point
        if theta in (0, 180):
            pass

    @staticmethod
    def get_change_in_x(x, radius, theta):
        return x + radius * math.cos(math.radians(theta))

    @staticmethod
    def get_change_in_y(y, radius, theta):
        return y + radius * math.sin(math.radians(theta))

    @staticmethod
    def get_slope_from_angle(theta):
        return math.tan(math.radians(theta))

    @staticmethod
    def invert_point(point):
        x, y = point
        return constants.WIDTH - x, constants.HEIGHT - y

    @staticmethod
    def pythagorean(a, b):
        return math.sqrt(pow(a, 2) + pow(b, 2))


class Gradient:
    def __init__(self, start, end, primary_color, secondary_color):
        self.start = start
        self.end = end
        self.primary_color = primary_color
        self.secondary_color = secondary_color

        self.slope = None
        self.slope_type = constants.SlopeEnum.DEFAULT
        self.perpendicular_slope = None
        self.interval = None
        self.interval_dim = None
        self.color_map = None

    @classmethod
    def create_new(cls, start, end, primary_color, secondary_color):
        gradient = cls(start, end, primary_color, secondary_color)
        gradient.gen_slope()
        gradient.gen_interval()
        gradient.gen_color_map()
        return gradient

    def gen_slope(self):
        x1, y1 = self.start
        x2, y2 = self.end
        try:
            m = (y2 - y1) / (x2 - x1)
        except ZeroDivisionError:
            self.slope_type = constants.SlopeEnum.VERTICAL
            return
        try:
            m1 = -1 / m
        except ZeroDivisionError:
            self.slope_type = constants.SlopeEnum.HORIZONTAL
            return
        self.slope = m
        self.perpendicular_slope = m1
        self.slope_type = constants.SlopeEnum.DEFAULT

    def gen_interval(self):
        dx = abs(self.end[0] - self.start[0])
        dy = abs(self.end[1] - self.start[1])
        self.interval = max(dx, dy)
        self.interval_dim = (
            constants.IntervalEnum.HORIZONTAL
            if dx > dy
            else constants.IntervalEnum.VERTICAL
        )

    def gen_color_map(self):
        self.color_map = self.interpolate(
            self.interval, self.primary_color, self.secondary_color
        )

    @staticmethod
    def interpolate(interval, primary_color, secondary_color):
        color_delta = [
            (right - left) / interval
            for left, right in zip(primary_color, secondary_color)
        ]
        for i in range(interval + 1):
            yield [
                round(color + delta * i)
                for color, delta in zip(primary_color, color_delta)
            ]


class Layer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.image = None
        self.drawing = None

    @classmethod
    def create_new(cls, width=constants.WIDTH, height=constants.HEIGHT):
        image = cls(width, height)
        image.gen_pil_image()
        image.gen_drawing()
        return image

    def gen_pil_image(self):
        self.image = Image.new("RGBA", (self.width, self.height), color=0)

    def save(self, filename):
        with open(filename, "wb") as f:
            self.image.save(f)

    def gen_drawing(self):
        self.drawing = ImageDraw.Draw(self.image)

    def apply_gradient(self, gradient):
        self.fill_edges(gradient)
        self.fill_gradient(gradient)

    def fill_gradient(self, gradient):
        # vertical/horizontal
        if gradient.slope_type != constants.SlopeEnum.DEFAULT:
            self.fill_linear_gradient(gradient)
        else:
            self.fill_gradient_impl(gradient)

    def fill_edges(self, gradient):
        if gradient.slope_type != constants.SlopeEnum.DEFAULT:
            self.fill_linear_edges(gradient)
        else:
            self.fill_polygon_edges(gradient)

    def fill_linear_edges(self, gradient):
        rectangle_map = {
            constants.SlopeEnum.HORIZONTAL: self.fill_horizontal_rectangles,
            constants.SlopeEnum.VERTICAL: self.fill_vertical_rectangles,
        }
        rectangle_map[gradient.slope_type](gradient)

    def fill_vertical_rectangles(self, gradient):
        self.drawing.polygon(
            [
                constants.Corners.TOP_LEFT,
                (constants.GRADIENT_OFFSET, 0),
                (constants.GRADIENT_OFFSET, constants.HEIGHT),
                constants.Corners.BOTTOM_LEFT,
            ],
            fill=gradient.primary_color,
        )
        self.drawing.polygon(
            [
                constants.Corners.TOP_RIGHT,
                (constants.GRADIENT_WIDTH + constants.GRADIENT_OFFSET, 0),
                (
                    constants.GRADIENT_WIDTH + constants.GRADIENT_OFFSET,
                    constants.HEIGHT,
                ),
                constants.Corners.BOTTOM_RIGHT,
            ],
            fill=gradient.secondary_color,
        )

    def fill_horizontal_rectangles(self, gradient):
        self.drawing.polygon(
            [
                constants.Corners.TOP_RIGHT,
                constants.Corners.TOP_LEFT,
                (0, constants.GRADIENT_OFFSET),
                (constants.WIDTH, constants.GRADIENT_OFFSET),
            ],
            fill=gradient.primary_color,
        )
        self.drawing.polygon(
            [
                constants.Corners.BOTTOM_RIGHT,
                constants.Corners.BOTTOM_LEFT,
                (
                    0,
                    constants.GRADIENT_HEIGHT + constants.GRADIENT_OFFSET,
                ),
                (
                    constants.WIDTH,
                    constants.GRADIENT_HEIGHT + constants.GRADIENT_OFFSET,
                ),
            ],
            fill=gradient.secondary_color,
        )

    def fill_linear_gradient(self, gradient):
        for i, color in enumerate(gradient.color_map):
            if gradient.interval_dim == constants.IntervalEnum.HORIZONTAL:
                coordinates = [
                    (i + constants.GRADIENT_OFFSET, 0),
                    (i + constants.GRADIENT_OFFSET, constants.HEIGHT),
                ]
            else:
                coordinates = [
                    (0, i + constants.GRADIENT_OFFSET),
                    (constants.WIDTH, i + constants.GRADIENT_OFFSET),
                ]
            self.drawing.line(
                coordinates,
                fill=tuple(color),
                width=1,
            )

    def fill_gradient_impl(self, gradient):
        start = gradient.start
        m = gradient.slope
        m1 = gradient.perpendicular_slope
        for i, color in enumerate(gradient.color_map, 1):
            # maybe need to update point...
            current_point = self.get_next_gradient_coords(
                m, start, i, gradient.interval_dim
            )
            first_intercept, second_intercept = self.get_intercepts(m1, current_point)
            self.drawing.line(
                [first_intercept, second_intercept],
                fill=tuple(color),
                width=math.ceil(abs(m)) + 1,
            )

    def fill_polygon_edges(self, gradient):
        """
        Identifies the three points that make up the corner polygons of solid
        color for the gradient.
        """
        start, end = gradient.start, gradient.end
        slope = gradient.perpendicular_slope
        quadrant = self.get_quadrant(start)

        first_intercept, second_intercept = self.get_intercepts(slope, start)
        corner = self.get_corner_from_quadrant(quadrant)
        self.drawing.polygon(
            [corner, first_intercept, second_intercept],
            fill=gradient.primary_color,
        )
        # invert the polygon for the ending point - secondary color
        oppo_corner = Coordinates.invert_point(corner)
        oppo_first_intercept = Coordinates.invert_point(first_intercept)
        oppo_second_intercept = Coordinates.invert_point(second_intercept)
        self.drawing.polygon(
            [oppo_corner, oppo_first_intercept, oppo_second_intercept],
            fill=gradient.secondary_color,
        )

    def trim(self):
        self.trim_interior()
        self.trim_edges()

    def trim_interior(self):
        interior = Image.new(
            "RGBA",
            (constants.GRADIENT_WIDTH - 80, constants.GRADIENT_HEIGHT - 80),
            color=0,
        )
        self.image.paste(interior, box=constants.INTERIOR_ORIGIN)

    def trim_edges(self):
        horizontal_edges = Image.new(
            "RGBA",
            (constants.WIDTH, constants.LAYER_OFFSET),
            color=0,
        )
        self.image.paste(horizontal_edges)
        self.image.paste(
            horizontal_edges,
            box=(0, constants.LAYER_OFFSET + constants.LAYER_HEIGHT),
        )
        vertical_edges = Image.new(
            "RGBA",
            (constants.LAYER_OFFSET, constants.HEIGHT),
            color=0,
        )
        self.image.paste(vertical_edges)
        self.image.paste(
            vertical_edges,
            box=(constants.LAYER_OFFSET + constants.LAYER_WIDTH, 0),
        )

    def blur(self, radius):
        self.image = self.image.filter(ImageFilter.GaussianBlur(radius))

    @staticmethod
    def get_next_gradient_coords(m, start, interval, interval_dim):
        x1, y1 = start
        if interval_dim == constants.IntervalEnum.HORIZONTAL:
            x2 = x1 + interval
            return x2, abs(m * (x2 - x1) + y1)
        else:
            y2 = y1 + interval
            return abs((y2 - y1) / m + x1), y2

    @staticmethod
    def get_intercepts(m, point):
        x, y = point
        return (0, y + (m * -1 * x)), (x + (-1 * y / m), 0)

    @staticmethod
    def get_quadrant(point):
        x, y = point
        if x < constants.GRADIENT_WIDTH / 2:
            return (
                constants.QuadrantEnum.FIRST
                if y < constants.GRADIENT_HEIGHT / 2
                else constants.QuadrantEnum.THIRD
            )
        else:
            return (
                constants.QuadrantEnum.SECOND
                if y < constants.GRADIENT_HEIGHT / 2
                else constants.QuadrantEnum.FOURTH
            )

    @staticmethod
    def get_corner_from_quadrant(quadrant):
        return {
            constants.QuadrantEnum.FIRST: constants.Corners.TOP_LEFT,
            constants.QuadrantEnum.SECOND: constants.Corners.TOP_RIGHT,
            constants.QuadrantEnum.THIRD: constants.Corners.BOTTOM_LEFT,
            constants.QuadrantEnum.FOURTH: constants.Corners.BOTTOM_RIGHT,
        }[quadrant]

    @staticmethod
    def add_gradient_offset(point):
        x, y = point
        return x + constants.GRADIENT_OFFSET, y + constants.GRADIENT_OFFSET

    @staticmethod
    def add_layer_offset(point):
        x, y = point
        return x + constants.LAYER_OFFSET, y + constants.LAYER_OFFSET


if __name__ == "__main__":
    # TODO: replace with circular coords class to rotate around the edge of
    # the gradient frame defining the coordinates to generate.
    x1, y1 = Layer.add_gradient_offset((1200, 0))
    start = (x1, y1)
    x2 = constants.WIDTH - x1
    y2 = constants.HEIGHT - y1
    end = (x2, y2)

    # Create a gradient
    gradient = Gradient.create_new(
        start, end, constants.Colors.CYAN, constants.Colors.MAGENTA
    )
    # Create a layer
    image = Layer.create_new(constants.WIDTH, constants.HEIGHT)
    # apply gradient
    image.apply_gradient(gradient)
    # trim the middle and edges
    image.trim()
    # add gaussian blur
    # image.blur(radius=10)

    coords = Coordinates.create_new(
        width=constants.GRADIENT_WIDTH,
        height=constants.GRADIENT_HEIGHT,
        degrees=3,
    )

    drawing = image.drawing
    guides.display_gradient_boundary(drawing)
    # guides.display_gradient_guidelines(drawing)

    print(coords.coords)

    for coord in coords.coords:
        start, end = coord
        drawing.line(
            [start, end],
            fill=constants.Colors.YELLOW,
            width=5,
        )

    a, b = 1920, 1080
    c = Coordinates.pythagorean(a, b)
    x1, y1 = a - c + 320, b - c + 320
    x2, y2 = x1 + c * 2, y1 + c * 2

    drawing.ellipse([(x1, y1), (x2, y2)], outline=constants.Colors.WHITE, width=5)

    # save
    image.save("img_result2.png")
