---
title: 'Khosla Hydraulic Foundation Designer: A desktop application for Khosla-based seepage, uplift pressure, and exit-gradient analysis'
tags:
  - Python
  - civil engineering
  - seepage analysis
  - uplift pressure
  - hydraulic structures
  - Khosla method
authors:
  - name: Kamran Ahmad
    affiliation: 1
  - name: Naima Noor
    affiliation: 1
affiliations:
  - name: Department of Civil Engineering, University of Engineering and Technology, Peshawar, Pakistan
    index: 1
date: 7 July 2026
bibliography: paper.bib
---

# Summary

*Khosla Hydraulic Foundation Designer* is an open-source desktop application for preliminary seepage, uplift-pressure, required floor-thickness, and exit-gradient analysis of hydraulic structures founded on pervious soil. The software implements Khosla's method of independent variables for common hydraulic-floor arrangements such as weirs, barrages, regulators, and canal falls. It provides a graphical workflow in which users enter water levels, floor geometry, cutoff-pile positions, material properties, and safety limits, then inspect pressure percentages, uplift heads, uplift pressures, required floor thicknesses, and exit-gradient safety status. The application also generates editable two-dimensional sections, conceptual three-dimensional views, tabulated calculation results, spreadsheet output, and a PDF engineering report.

The target users are civil engineering students, instructors, and early-stage design engineers who need a transparent tool for learning or checking classical hydraulic-floor calculations. The software is not intended to replace detailed geotechnical investigation or numerical seepage modeling for final design of major hydraulic structures.

# Statement of need

Seepage below a hydraulic structure can generate uplift pressure under the impervious floor and a concentrated hydraulic gradient at the downstream exit. If these effects are not checked, the floor may crack or lift and foundation soil may be removed by piping. Khosla's method remains a standard classical procedure for estimating pressure percentages below hydraulic floors and for checking uplift and exit-gradient conditions [@khosla1954]. However, manual use of the method is error-prone because the user must interpret the geometry, classify end and intermediate piles, identify E, D, and C pressure points, assign correction terms, and then convert corrected pressure percentages into uplift-pressure and floor-thickness checks.

Existing teaching resources commonly present the method through static textbook diagrams and hand calculations. Such material is useful for theory, but it does not provide an interactive connection between the hydraulic-floor geometry and the tabulated calculation results. The present software addresses this gap by placing the calculation engine, section drawing, safety status, and report generation in one desktop workflow. This makes the tool useful for classroom demonstrations, checking textbook-style problems, and preparing transparent preliminary design reports.

# State of the field

Classical approaches to seepage safety include creep-length methods and independent-variable methods. Lane's weighted-creep method provides a global check of under-seepage safety [@lane1935], while Khosla's method gives pressure percentages at specific locations below a hydraulic floor [@khosla1954]. Modern engineering projects may use finite element, finite difference, or field-calibrated seepage analyses when soil layering, anisotropy, transient flow, drains, filters, or three-dimensional effects are important [@usace1993].

The contribution of *Khosla Hydraulic Foundation Designer* is not to replace numerical seepage packages. Instead, it fills a narrower educational and preliminary-design need: a lightweight open-source desktop tool that explains and applies Khosla-based calculations with visible geometry, correction terms, and reproducible reports. The build decision is justified because general numerical modeling environments require more site data and specialist modeling choices, whereas the intended users often need a direct and auditable implementation of a classical civil engineering method.

# Software design

The software is organized around a small number of engineering modules. The input module stores project information, hydraulic levels, floor geometry, pile locations, material parameters, and safety limits. The calculation engine sorts pile lines by station, classifies them as upstream end, intermediate, or downstream end piles, and evaluates the relevant Khosla pressure percentages and correction terms. The output module reports base pressure percentage, mutual interference correction, thickness correction, slope correction, corrected pressure percentage, residual uplift head, uplift pressure, required thickness, provided thickness, exit gradient, and safety status.

A design feature of the software is the node-based floor-thickness model. Instead of treating floor thickness as an isolated pile attribute, thickness is defined through station-thickness nodes along the hydraulic floor. The local thickness at a calculation point is then interpolated between adjacent nodes. This design choice keeps the drawn floor geometry, floor-thickness correction, and provided-versus-required thickness comparison consistent. It also makes the program easier to audit because the same physical thickness schedule is used by both the visual model and the calculation model.

The graphical interface provides a design workspace, result table, step-by-step calculation report, editable two-dimensional section, conceptual three-dimensional section, and export tools. The repository includes sample inputs, screenshots, exported validation reports, a license file, citation metadata, and documentation for installation and use.

# Validation and reproducibility

Validation material is supplied with the repository so that reviewers and users can reproduce the reported behavior. The included barrage/weir example uses a total floor length of 72.000 m, pond level of 102.363 m, tail-water level of 100.000 m, and seepage head of 2.363 m. Three pile lines are defined at 0.000 m, 42.000 m, and 72.000 m, with cutoff depths of 5.975 m, 6.000 m, and 4.000 m, respectively. The exported results include corrected pressure percentage, uplift head, uplift pressure, required floor thickness, provided floor thickness, and safety status at selected points. In this example, the computed exit gradient is 0.060970, which is below the allowable value of 0.166700; the software therefore reports the exit-gradient condition as safe.

The validation files are intended to support transparent checking rather than to claim universal design validity. For major structures, users should supplement the software output with professional review, site-specific geotechnical information, and appropriate numerical or field-calibrated seepage analysis.

# Research impact statement

The software provides credible near-term scholarly value by making a classical hydraulic-structure design method reproducible and inspectable through open-source files, a versioned release, sample cases, validation material, and a DOI-citable archive [@ahmad2026khosla]. It can support civil engineering education by allowing students to compare manual calculations with software outputs and by helping instructors demonstrate the relationship between floor geometry, pressure points, correction terms, uplift pressure, floor thickness, and exit-gradient safety. It can also support early-stage design studies where transparent screening calculations are required before more detailed seepage analysis is justified.

# AI usage disclosure

Generative AI assistance was used for language editing, formatting support, and preparation of publication-oriented manuscript text. The authors remain responsible for verifying all equations, software behavior, validation outputs, repository files, citations, and engineering conclusions before submission.

# Acknowledgements

The authors acknowledge the Department of Civil Engineering, University of Engineering and Technology, Peshawar, Pakistan, for the academic context in which this software was developed. No external funding was received for this work.

# References
