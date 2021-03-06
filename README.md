# scanomatic (python module) and Scan-o-matic (program

This project contains the code for the massive microbial phenotyping platform Scan-o-matic.

Scan-o-matic was published in [G3 September 2016](http://g3journal.org/content/6/9/3003.full).

Please refer to the [Wiki](https://github.com/local-minimum/scanomatic/wiki) for instructions on use, installation and so on.

If you are considering setting up Scan-o-matic at your lab, we would be very happy and would love to hear from you. But, before you decide on this, the Faculty of Science at University of Gothenburg has included Scan-o-matic among its high-throughput phenomics infrastructure and it is our expressed interest that external researchers come to us. If you are interested there's some more information and contact information here: [The center for large scale cell based screeening](http://cmb.gu.se/english/research/microbiology/center-for-large-scale-cell-based-screening). It is yet to become listed on the page, but don't worry, it will be part of the list.


__The rest of this file here will only discuss code-related issues.__

# Features that would be nice if included

* Ability to calibrate and add a new grayscale with using old as refernce.
* Validation of that a grayscale is producing acceptable values in a scanner over time
* Showing of gridding in Status and QC-view. (API exists, viewing in regridding exists)
* Showing of logfiles for a project at various stages and views (API exists).
* Showing of the instructions given at various stages to Scan-o-matic (API exists).
* `scan-o-matic_as_service_check` script should allow for reboot as well
* Fixture creation image selection should allow to select file on server as well as uploading image
* Fixture creation should have magnification of what is hovered.
* Scan.instructions could include more scanner information such as actual `scanimage` argument string used.
* Gridding could attempt to use heuristics or history about grids to assist gridding and/or warn users
* Add 16 BIT image scanning?

