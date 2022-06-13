# CRAML: Context Rule-Assisted Machine Learning #
Welcome to CRAML Beta Version 0.4! CRAML is a novel text classification and dataset creation framework that harmonizes expert domain-level knowledge with the power of Machine Learning, in order to create meaningful datasets from raw data.

## What is it?! ##
 Do you have raw, unstructured text data and wish to create labeled datasets for downstream tasks? Then CRAML is right for you! Tackling the persistent problem of manually painstaking and resource intensive process of annotating large amounts of data, CRAML introduces a hybrid process that still leverages the speed and predictive power of Machine Learning methods, while resting upon the foundation of manually verified context rules. This can all be done in one single UI, which takes you from the raw data (which you provide) to a **clean, structured, codified dataset**. Pretty neat.

## Prerequisites ##
There's not much you need to begin, but here's a few things:  

- Any OS (but Linux recommended!)  
- Python 3.x installed  
- Some text data (+metadata, optional) in `csv` or `xml` format (or zipped) --> example files have been included  
- This repository cloned to your local computer  
- Run the command: `pip install -r requirements.txt` (to install all Python dependencies)  

 And then you're good to go!

## Starting Up ##
The only important step to complete before firing up CRAML is to take note of the format and location of your input data. For CRAML, two basic input types are in play:  

1. **Text Data**: these are the files that contain the *text* field to be extracted and processed. Of course, these files can also contain other fields, which can be included later on. The text is most important, as the context rules are created from here.  
2. **Meta-Data**: this type of input is optional, in the case that metadata is contained in separate files outside of those included with the text data. 

Both input types should already be "semi-structured", i.e. contained in `csv` or `xml` format, ideally with a unique identifier field. The goal is now to take these inputs, and output a unified and labeled dataset.

With these in hand, all you need to do is run: `CRAML_Tool.py`. This will open the CRAML UI in your default browser as a locally-hosted web application. Note that you must run the file from its original location. As an alternative for Windows users, navigate to the `CRAML_Tool` directory and try out **CRAML_Tool.exe**.

## Navigating CRAML ##
The UI features a straightforward navigation, with the different stages of the CRAML framework separated to allow for flexibility and ease of use. These stages can be found in the left navbar. Each page is introduced below.

### Home ###
Self-explanatory: start here!

### Project ###
The CRAML UI allows for the user to carry out multiple projects at once. Each project contains its own files, rules, classifiers, etc. This can be useful if you have multiple data corpora you would like to work with. In this tab, select which project you're going to be working on, or create a new one!

### Setup ###
The Setup stage is important to setting the parameters of your project. The page will prompt you to select one or two input types, i.e. if you only have **Text Data** files, or if you also have separate **Meta-Data** files. You can then upload "example" files for each of these (does not matter which, just choose the *prototypical* file for each input type). Upon doing this, you choose which fields to keep, which field is the unique identifier, and most importantly: which field is the *text* field to be extracted and processed. Note that **one and only one** field can be this *text* field - otherwise things would just get confusing! 

A few notes to the several options available to you:

* **Parent Directory**: this is the relative filepath from your working directory (where `CRAML_Tool.py `is located) to where the "example" file is located, and presumably the rest of the files similar to it. If for some reason the file type (extension) of the example file does not match with the rest of the files, feel free to change this using the provided dropdown.
*  **File Explorer**:  once you input the path and file type, a list of file will automatically show up - this is simply all of the files in that directory matching the specified file type. Select which ones of these you will need (that have the text data), or `SELECT ALL`. 
*  **ID, Extract Fields**: two dropdowns are presented next. The ID fields is mandatory: each input type (at least 1, maximum 2) should have an ID field, which uniquely indicates rows. If using two input file types, the IDs must not have the same name, but must "match up".
*  **File Extraction -- IMPORTANT!**: if the indicated *Extract* field (which field is your text data) is not actually present in the file itself, but rather is filename pointing to the actual text file, flip the provided switch. If you do so, next you must provide the relative path to where these text files are located.
*  **Fields to keep**: this is up to you! Of course, you will need at least an identifier field, as well as one text field for extraction. As you click or unclick these fields, the options for the two dropdowns above will dynamically change. 

When you're satisfied with the setup, click `Save`. You can always come back later and modify the setup.

### Sample ###
Think of this stage as the selection of "training data" for your eventual classifiers. As the goal is to eventually train models that will automatically annotate your data, we must first hold out a sample from the entire data to serve as training data. Simply enter the relative location of the **Text Data** files, and choose your sampling rate - this rate is up to you (but we recommend 10-25%). Click `Sample` to perform this sampling, or `Clear` to reset.

### Tags ###
Along with **Rules**, this tab represent the crux of the CRAML process. Essentially, tags help answer the question: *what do I want to discover or learn about my data?* Think about each tag as a binary, yes/no answer to some overarching theme. For example, if your text data is movie reviews, maybe you want a tag called `glowing`, which you define to be *a review that sings high praise for a movie*. For each tag, you can then define keywords or key phrases which you believe to embody this tag in question. Continuing with the `glowing` example, you might select *awesome*, *action-packed*, *ten out of ten*, to name a few. These are entirely up to you! The shorter the better, as these are the "base" units for each tag you define.

To create a new tag, click `+`. To remove one, click `-`. Navigate the tag tabs to see each of your tags. To add a new keyword, click `ADD KEYWORD` and enter the new keyword (or phrase!) in the corresponding table. When you wish to save a tag's keywords, click `SAVE KEYWORDS` (do this often!). 

### Rules ###
With your tag(s) in hand, it now becomes time to perform the important manual work that is crucial to CRAML. Here, you (as the "domain expert") are in control of your tag(s) -- by defining **context rules**, you essentially shape the meaning / definition of each tag. In this way, it is useful to have a good idea of the kinds of **contexts** in which the keywords and key phrases may frequently appear. To illustrate this, let's introduce a new mini-example (perhaps silly, [inspiration - yum!](https://www.buzzfeed.com/hannahloewentheil/recipes-that-take-a-long-time)), where some keywords may not be so clear cut when out of context:

* **Data**: Cooking Recipes
* **Tag**:  LongPrepTime
* **Keywords**: *hour*, *slow*, *dough*, *homemade*

| Rule        | Priority | LongPrepTime           
| ------------- |:-------------:|:-------------:
| hour     | 0 | 0
| slow    | 0 | 0
| homemade  | 0 | 0  
| dough | 0 | 0
| 1 hour | 1 | 0
| 2 hours | 1 | 1
| 3 hours | 1 | 1
| slow cooker | 1 | 1
| slowly pour | 1 | 0
| slow roast | 1 | 1
| unpackage the dough | 1 | 0
| roll the dough | 1 | 1
| homemade dough | 99 | 1

Some important concepts here. By default, all keywords are included in the rules as 0 (tag = False), and it is highly recommended that this is kept. This can be safely done, as the **Priority** of a rule will override a previously identified rule. For example, the existence of "slow" in a recipe does not necessarily imply a long prep time, but "slow roast" might be a much better indicator. Priorities are purely ordinal, so feel free to choose whatever values you like, as long as they reflect the desired ranking!

On the **Rules** page, click `+` to add a new rule file, or `-` to delete one. Note that a newly created rules file can contain one or more of your defined tags. As stated, a newly created file will by default contain all the keywords of the contained tags. Click `ADD RULE` to fill in a new rule, and `SAVE RULE` to save changes.

The example given above is obviously contrived and by no means complete. Good news - you can make each rule file as involved (or not) as you want. The rest of the CRAML process will guide you regarding this, and as always, you can come back and edit the rules.

### Extract ###
Now that you've created your tags and rules, it's time to test these out with your sample (training) data. This process will prepare the training datasets to be used for the training of your classifiers. Extraction will incorporate all of your current keywords and their corresponding rules. Here, you have three decisions to make:

1. **Extract Sample** vs. **Full Dataset Extract (Full Extract)**: if your goal is to use a sample of your data to train a ML classifier, then choose to extract a sample. Assuming you have already navigated to the **Sample** page and prepared a data sample, this process will now perform an extraction on the sample. If instead you choose to do a Full Extract, the extraction process will be performed on the *entirety* of your original data. This can be helpful for producing a fully-ready, structured dataset that exactly captures your defined keywords and rules. The choice is yours.
2. **Word** chunks vs. **sentence** chunks: for context windows, do we want to consider the n-number of word neighbors or sentence neighbors. As a general rule of thumb, contexts that are largely phrase-driven should use chunking, and contexts that potentially contain larger scopes (think bigger documents) should use sentence chunking. Or test both out!
2. **N**: this is simply the number or word or sentence chunks to include to the left and right of your keywords. In the case of word chunks, N refers to the *maximum* context windows, and will be truncated at punctuation (on either side).

On the **Extract** page, you can keep track of your different extract jobs, which a uniquely identified. Remove jobs (and their output data) that you no longer need. Or click on the ids to proceed to the next step: text exploration.

### Context Exploration ###
While the process of tag and rule creation can be largely based on your expertise in the domain in question, you may not know *every* kind of context in which these key words or phrases pop up. Or, you may just want some more ideas for meaningful rules.

The **Context Exploration** page helps you accomplish this by allowing you to peek into your extracted sample data, to see what are the most frequent text chunks that appear in your text data. First select a completed **Extract** job, then choose a tag to explore. Next, choose whether you want to see the most frequently appearing chunks (*Top-X*) or a random assortment (*Random-X*). Then, select the value of *X*. Finally, pick which *Context Size* you would like to investigate - naturally, the max choice is the value of *N* you chose at the time of extraction, but you can also choose smaller values (think of this as "trimming"). Hit `Run`!

Depending on the size of your data, this make take a short while. Once it's down, it's time to explore! Scroll through the results, and look at the frequency with which certain chunks of texts appear in your data. In essence, you're performing a n-gram analysis of your data. If you see a chunk that seems to be a good candidate for a rule, click on the cell, and then click `ADD SELECTED`. This will open a dialog. Here, you can edit the rule (in the case you want to trim off some unnecessary parts), and then you must choose which rule file it belongs to. Once you do this, you will be prompted to fill in the necessary *priority* information, as well as the appropriate 0/1 value for each tag.

**Important**! While the pages are described here sequentially, the CRAML process is by no means that! It is designed to be an iterative process: tag definition, rule creation, extraction and exploration, discovery of new rules, repeat. This will help to create more robust rule sets, which plays a necessary role in the following.

### Validation ###
In the case that you opted to perform a *Full Extract* during the **Extract** process, it could be extremely helpful to perform a manual validation of the results. Particularly when Regular Expression rules are used, the results of the extrapolated dataset may vary. Therefore, the **Validation** page was created the verify the data produced by the Full Extract.

To begin, select a Full Extract job that has finished. Next, select which rule set you would like to verify. The other two options are: (1) minimum instances per rule: if available, how many data instances per rule would you like in the validaton set, *at a minimum*? (2) number of training instances: how many total instances would you like? Note that because of the former option, the final number in the later may vary. Depending upon the number of minimum instances chosen, the lower bound for the number of total instances might change. If this number is chosen to be too low, the UI will inform you of the current required minimum number.

Once these options are chosen, click `Generate`. Depending on the size of your data and the options chosen, this process may take up to several minutes. Also note that the selection of entries is random, so repeated runs with the same settings will produce different validation sets. When ready, the results will display in the table. To start the manual validation, scroll through the table and fill in the `truth` column with the ground truth label. For reference, the text chunk and rule that led to each classification is listed to aid in the manual validation. 

At any point, you are able to export the current state of the table to a CSV file. You can store the results, or continue to annotate the table offline. If your would like to import the file back into the UI, simply choose `Import`. Likewise, if you leave the page at some point, you can navigate back and choose `Reload` to load previous validation sets **matching the current options**. 

The final step to do (once all labels are filled in!) is to click `Score`. This will calculate of number of common metrics, as well as a confusion matrix illustrating the validation results. This will be immediately displayed on-screen, as well as saved locally in the project folder (under `project/val`). Now you can explore with different settings!

### Train ###
At this point, we make the necessary transition from rather manual, yet meaningful, work to the realm of text classification by way of Machine Learning (ML) models. The main motivation here is that we first put the work in to create solid foundations for our defined tags, but then make our rules generalizable via model training. Of course, we could use purely our rule sets as rudimentary, matching-based, high-precision classifiers, but this would fall short to detect cases not contained within our rule sets (unless we somehow believe to *fully define* the tag in its rule set). So, we turn to ML.

The current Beta version 0.1 contains two options for training: Naives Bayes [**Train (NB)**] and Random Forests [**Train (RF)**]. In initial testing and development, these were found to be the best two foundational options: NB for its simplicity and RF for its relative power vs. complexity. In the CRAML framework, we train one classifier for each defined tag, thereby creating a binary text classification model for each tag. 

Navigate to your desired choice of classifier's page, select which extracted directory (i.e. training data) to use, and then pick which rules file to train on (which will determine which and how many classifiers are trained). Both training pages have the option of *Negative Sampling*. This process introduces extra "negative" cases (tag=0) into your training data that would have not been included by way of your rules file. Utilizing this option has the potential to make your model more robust, although this can be data-dependent. Another option is *Sample Rate*: this is simply what percentage of your training data do you actually want to train on. For larger training sets, it may make sense to set a lower value, in order to reduce classifier size (and classification time later on).

In the case of **Train (RF)**, three additional settings are included, which are specific to Random Forests. Feel free to experiment with these if your are familiar with the settings; otherwise, no need to change anything!

When satisfied with your settings, click `TRAIN!`. Track the training progress it the table provided. When the status reads "Finished", your model is ready to go. Select the row and click `SHOW RESULTS` to see some information / diagnostics of the training process.

### Dataset Creation ###
Here is where all your hard work pays off! The **Dataset Creation** page will finished the CRAML pipeline with its output being the final dataset based upon your tags, rules, and classifiers. First, four settings categories to complete:

1. **Rules**: select which rule files (i.e. which tags) you want included in your dataset.
2. **Extrapolate**: which mode (word vs. sentence) and context size (N) should be used? While you can technically choose different settings than what you chose before to train on, it is recommended to stick to the same choice (you can vary *N* slightly if you want).
3. **Save**: how do you want your data saved? *Keep Text?* refers to whether you would like to include the extracted text field in your dataset. *Save to Database*? will decide whether your dataset is stored in a database (currently: **SQLite**), or simply a CSV file. If you choose to save to a database, more options will appear as to your *Database Name*, *Table Name*, as well as the data type for each included field - fill all these out. By default, the extracted text field must be of type `TEXT`.
4. **Classifiers**: you may have trained several classifiers for a particular tag - choose which one you want to be used for this dataset creation. One classifier per tag.

When everything is filled out, hit `RUN!` This will set off the dataset creation process. Note that this will take a while (depending on your data): feel free to close the CRAML Tool and grab a coffee or a nap. All processes (including those from the other pages) will chug along on their own, and the tool will keep track of their progress upon return. When the status says "Finished", your dataset was successfully completed!

### Dataset Exploration ###
As a final (optional) stage, the **Dataset Exploration** page will allow you to explore your newly created datasets. This may be helpful to see how they turned out, or to verify if the text is indeed classified according to your definition of the tools. Think of this almost as Text Exploration, pt. 2. Similar to before, select a dataset, as well as the mode and number of the results to be shown. Click `GO!`.

Like the **Context Exploration**, **Dataset Exploration** is also meant to be part of a continuous loop in the CRAML framework. Don't like how some results turned out? Head back to your rules! See some new recurring themes within your text data? Define a new tag! Everything is up to you.

## Utilities ##
The CRAML Tool includes a few utilties that are meant to be helpful during the entire process, particularly with exploring and preparing your data. These utilities are outlined below.

#### File Explorer ####
This utility will allow you to open and browse files that are created and maintained during the CRAML process. Sometimes it may be helpful to view your rules files in your preferred file editor, for example. In addition, the intermediate results produced by the extract stage can also be explored.

There are two ways to explore your files. Directly from the **Extract** page, click on the status of a `Finished` process to be redirected to the file explorer with these results pre-loaded. Otherwise, you can navigate straight to the **File Explorer** page and choose from the dropwdown list of completed processes. 

#### PDF-To-Text ####
Have a corpus of PDF files with text that you would like to through CRAML? The **PDF-To-Text** tool will help you quickly convert these files to plaintext files, which is the most convenient form for use in CRAML. Simply input the parent directory of these files and let the tool go to work. Note: the tool will mimic the subdirectory structure of the parent directory, as well as keep the filenames intact. For example, `parent/child/test.pdf` will be converted to `data/text/child/test.txt` in the corresponding project folder.

In the case where you already have text files but would like to clean the text, simply choose the option on the **PDF-To-Text** page in order to only clean the text. Similarly, when converting from PDF files, you have the option to clean the resulting text or not.

#### Metadata Maker ####
If you remember from the **Setup** page, each document to be analyzed via CRAML needs to be uniquely identified, essentially so that the resulting dataset in the end can have a ID column. If just have a collection of text documents with no pre-existing metadata, this identifier might no exist. To help solve this, the **Metadata Maker** tool will map uniquely generated IDs to all documents in your project, thus creating the necessary file to be indicated in the **Setup** process. This is most helpful when you have many "unstructured" documents (such as those converted in the **PDF-To-Text** utility). The result of using this utility will then be a simple file with an ID column, which is mapped to the filenames.

## DocumentCloud (Beta) ##
Curreently in development is a DocumentCloud Add-In which will allow users to integrate their DocumentCloud accounts with the CRAML interface. [DocumentCloud](https://www.documentcloud.org/home) is an:

> ...all-in-one platform for documents: upload, organize, analyze, annotate, search, and embed.

Most importantly, is serves as a repository for millions of publicly available documents, making it a perfect place to source your data for CRAML. 

Future functionality will include importing and annotating DocumentCloud documents. With these users can create structured datasets from any number of available documents on the platform. Stay tuned.

## Get CRAMLing! ##
We hope that this brief guide will allow you to begin your CRAML journey. Should questions, comments, or bugs arise, please feel free to reach out. Stay tuned for updates and improvements!
