# Decisions

## 2026-10-01: Distribution name

The `slopmeter` distribution name is already occupied on PyPI. The project uses the available
distribution name `slop-meeter` while preserving the planned `slopmeter` import package and CLI.

## 2026-10-01: License

Use the plan's default MIT license because no owner override was provided.

## 2026-10-01: Placeholder density denominator

`D5` divides empty Python functions plus TODO/lorem markers by the number of Python functions plus
markers. This deliberately makes explicit markers visible even in repositories with little Python.
